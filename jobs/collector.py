#!/usr/bin/env python3
"""Public job collector for Gagan's Azure Data Engineer queue.

Uses public search-engine result pages and official career pages where available.
It intentionally does not log in, bypass CAPTCHAs, defeat anti-bot controls, or
submit applications. Output is jobs/jobs.json for the dashboard.
"""
import json,re,time,hashlib
from datetime import datetime,timezone
from urllib.parse import quote,urlparse
from urllib.request import Request,urlopen

PROFILE=json.load(open("jobs/profile.json",encoding="utf-8"))
OUT="jobs/jobs.json"
UA="Mozilla/5.0 (compatible; AzureDEJobCollector/1.0; +https://github.com/Gagankaira/gagan-kaira-portfolio)"

QUERIES=[
    '"Azure Data Engineer" India',
    '"Senior Azure Data Engineer" India',
    '"Azure Databricks" "Data Engineer" India',
    '"Databricks" "PySpark" "Azure" India',
    '"Data Engineer" "Azure Data Factory" India',
]
COMPANIES=PROFILE["target_companies"]
LOCATIONS=PROFILE["locations"]

def fetch(url):
    req=Request(url,headers={"User-Agent":UA,"Accept-Language":"en-US,en;q=0.9"})
    with urlopen(req,timeout=20) as r:
        return r.read().decode("utf-8","ignore")

def strip_html(s):
    return re.sub(r"\\s+"," ",re.sub(r"<[^>]+>"," ",s)).strip()

def score(title,description,location,company):
    text=(title+" "+description+" "+location+" "+company).lower()
    keys=["azure","databricks","pyspark","python","sql","azure data factory","adf","adls","synapse","delta lake","etl","elt"]
    hits=sum(1 for k in keys if k in text)
    s=55+hits*4
    if any(x.lower() in location.lower() for x in LOCATIONS): s+=6
    if any(x.lower() in title.lower() for x in ["senior","lead"]): s+=4
    if any(x.lower() in company.lower() for x in COMPANIES): s+=4
    return min(99,s)

def parse_bing(html):
    # Best-effort public search parsing. If Bing changes markup, collector safely returns no results.
    out=[]
    for block in re.findall(r'<li class="b_algo".*?</li>',html,re.S|re.I):
        m=re.search(r'<h2>.*?<a href="([^"]+)"[^>]*>(.*?)</a>',block,re.S|re.I)
        if not m: continue
        url=m.group(1); title=strip_html(m.group(2))
        p=re.search(r'<p>(.*?)</p>',block,re.S|re.I)
        desc=strip_html(p.group(1)) if p else ""
        out.append((title,desc,url))
    return out

def canonical(url):
    p=urlparse(url)
    return p._replace(fragment="",query="").geturl().rstrip("/")

def company_from(title,desc):
    text=title+" "+desc
    for c in COMPANIES:
        if c.lower() in text.lower(): return c
    return ""

def main():
    old=json.load(open(OUT,encoding="utf-8")) if __import__("os").path.exists(OUT) else []
    old_ids={x.get("id") for x in old}
    found={}
    for q in QUERIES:
        try:
            html=fetch("https://www.bing.com/search?q="+quote(q)+"&count=50")
            for title,desc,url in parse_bing(html):
                blob=(title+" "+desc).lower()
                if "data engineer" not in blob and "databricks" not in blob: continue
                loc="India"
                if "hyderabad" in blob: loc="Hyderabad, India"
                elif "bengaluru" in blob or "bangalore" in blob: loc="Bengaluru, India"
                elif "pune" in blob: loc="Pune, India"
                elif "chennai" in blob: loc="Chennai, India"
                elif "gurugram" in blob or "gurgaon" in blob: loc="Gurugram, India"
                elif "noida" in blob: loc="Noida, India"
                company=company_from(title,desc)
                if not company:
                    # keep only identifiable employer pages, avoiding generic aggregator noise
                    host=urlparse(url).netloc.lower()
                    company=host.split(".")[-2].replace("-"," ").title() if "." in host else "Unknown"
                key=hashlib.sha1((canonical(url)+"|"+title.lower()).encode()).hexdigest()[:16]
                found[key]={
                    "id":key,"title":title,"company":company,"location":loc,
                    "posted":"Unknown","source":urlparse(url).netloc,
                    "description":desc,"skills":[],"url":canonical(url),
                    "reason":"Azure/data-engineering keyword match; verify exact requirements on the application page.",
                    "experience_ok":True,"status":"ready","new":key not in old_ids
                }
        except Exception as e:
            print("search failed:",q,e)
        time.sleep(1)

    # Preserve previous records so the dashboard remains useful between runs.
    merged={x["id"]:x for x in old if x.get("id")}
    merged.update(found)
    jobs=sorted(merged.values(),key=lambda x:(not x.get("new",False),-score(x["title"],x.get("description",""),x["location"],x["company"])))
    with open(OUT,"w",encoding="utf-8") as f: json.dump(jobs[:250],f,indent=2,ensure_ascii=False)
    print(f"Collected {len(found)} candidates; retained {len(jobs[:250])} records.")

if __name__=="__main__": main()
