"""Local JSON API for fictional A320 quality records."""
import csv, io, json, os, random, sqlite3, threading
from contextlib import closing
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
DB = Path(os.environ.get("QUALITY_DB", ROOT / "data/quality.db"))
PUBLIC = ROOT / "app/static"
LOCK = threading.Lock()

def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    return db

def init_db():
    with closing(connect()) as db:
        db.executescript((ROOT / "app/schema.sql").read_text())
        db.commit()
        if db.execute("SELECT COUNT(*) FROM aircraft").fetchone()[0]:
            return
        rng = random.Random(3202027)
        sites = ["Hamburg","Toulouse","Mobile","Tianjin"]
        areas = ["Cabin","Fuselage","Electrical","Avionics","Paint","Systems"]
        for a in range(1,121):
            aid = f"SIM-MSN-{10000+a}"
            delivery = date(2027,1,1) + timedelta(days=a)
            db.execute("INSERT INTO aircraft VALUES (?,?,?,?)",(aid,sites[(a-1)%4],"A321neo" if a%3==0 else "A320neo",delivery.isoformat()))
            for k in range(1,9):
                idx=(a-1)*8+k
                result=rng.choices(["Pass","Fail","Observation"],weights=[65,20,15])[0]
                db.execute("INSERT INTO inspections VALUES (?,?,?,?,?)",(f"INSP-{idx:05d}",aid,(date(2026,7,1)+timedelta(days=(idx-1)%120)).isoformat(),areas[(idx-1)%6],result))
            for k,stage in enumerate(["Final inspection","Documentation review","Customer handover"],1):
                idx=(a-1)*3+k
                db.execute("INSERT INTO milestones VALUES (?,?,?,?,?)",(f"MS-{idx:05d}",aid,stage,delivery.isoformat(),rng.choice(["Planned","Completed","At Risk"])))
        for n,inspection_number in enumerate(rng.sample(range(1,961),365),1):
            db.execute("INSERT INTO findings VALUES (?,?,?,?,?)",(f"FND-{n:05d}",f"INSP-{inspection_number:05d}",rng.choices(["Low","Medium","High","Critical"],weights=[40,35,20,5])[0],rng.choice(["Open","In Progress","Closed"]),rng.choice(["Surface finish observation","Functional test deviation","Component labeling discrepancy","Documentation mismatch"])))
        for n,finding_number in enumerate(rng.sample(range(1,366),314),1):
            db.execute("INSERT INTO actions VALUES (?,?,?,?,?)",(f"ACT-{n:05d}",f"FND-{finding_number:05d}",f"Coordinator {rng.randint(1,8)}",(date(2026,9,1)+timedelta(days=rng.randrange(160))).isoformat(),rng.choice(["Open","In Progress","Closed"])))
        db.commit()

def query(sql,args=()):
    with closing(connect()) as db:
        return [dict(r) for r in db.execute(sql,args).fetchall()]

def summary(site="All"):
    where="" if site=="All" else "WHERE a.site=?"
    args=() if site=="All" else (site,)
    return query(f"""SELECT a.aircraft_id,a.site,a.family,a.planned_delivery,
      COUNT(DISTINCT i.inspection_id) inspection_count,
      COUNT(DISTINCT f.finding_id) finding_count,
      COUNT(DISTINCT CASE WHEN f.status!='Closed' THEN f.finding_id END) open_findings,
      COUNT(DISTINCT CASE WHEN f.status!='Closed' AND f.severity IN ('High','Critical') THEN f.finding_id END) high_open,
      COUNT(DISTINCT CASE WHEN ac.status!='Closed' AND ac.due_date < date('now') THEN ac.action_id END) overdue_actions
      FROM aircraft a LEFT JOIN inspections i ON a.aircraft_id=i.aircraft_id
      LEFT JOIN findings f ON f.inspection_id=i.inspection_id
      LEFT JOIN actions ac ON ac.finding_id=f.finding_id
      {where} GROUP BY a.aircraft_id ORDER BY a.aircraft_id""",args)

def analytics(site="All"):
    rows=summary(site)
    by_site={}
    for r in rows:
        item=by_site.setdefault(r["site"],{"site":r["site"],"aircraft":0,"open":0,"high":0,"overdue":0})
        item["aircraft"]+=1
        for src,dst in (("open_findings","open"),("high_open","high"),("overdue_actions","overdue")):
            item[dst]+=r[src]
    return {"metrics":{"aircraft":len(rows),"inspections":sum(r["inspection_count"] for r in rows),"findings":sum(r["finding_count"] for r in rows),"open":sum(r["open_findings"] for r in rows),"high":sum(r["high_open"] for r in rows),"overdue":sum(r["overdue_actions"] for r in rows)},"by_site":list(by_site.values()),"aircraft":rows}

def aircraft_detail(aid):
    aircraft=query("SELECT * FROM aircraft WHERE aircraft_id=?",(aid,))
    if not aircraft:return None
    return {"aircraft":aircraft[0],
            "inspections":query("SELECT * FROM inspections WHERE aircraft_id=? ORDER BY inspection_date DESC",(aid,)),
            "findings":query("""SELECT f.*,i.area,i.inspection_date,ac.action_id,ac.owner,ac.due_date,ac.status action_status FROM findings f JOIN inspections i ON i.inspection_id=f.inspection_id LEFT JOIN actions ac ON ac.finding_id=f.finding_id WHERE i.aircraft_id=? ORDER BY f.finding_id""",(aid,)),
            "milestones":query("SELECT * FROM milestones WHERE aircraft_id=?",(aid,))}

def update_status(table,key,identifier,status):
    if status not in ("Open","In Progress","Closed"):raise ValueError("Invalid status")
    if table not in ("actions","findings"):raise ValueError("Invalid table")
    with LOCK,closing(connect()) as db:
        cur=db.execute(f"UPDATE {table} SET status=? WHERE {key}=?",(status,identifier))
        if not cur.rowcount:raise LookupError("Record not found")
        db.commit()
    return {"id":identifier,"status":status}

def update_action(action_id,status):
    return update_status("actions","action_id",action_id,status)

def update_finding(finding_id,status):
    return update_status("findings","finding_id",finding_id,status)

def feasibility():
    return query("SELECT * FROM requests ORDER BY id DESC")

def add_request(payload):
    title=str(payload.get("title","")).strip()[:120]
    detail=str(payload.get("detail","")).strip()[:800]
    priority=payload.get("priority","Medium")
    if len(title)<5:raise ValueError("Feature title must be at least 5 characters")
    if priority not in ("Low","Medium","High"):raise ValueError("Invalid priority")
    with LOCK,closing(connect()) as db:
        cur=db.execute("INSERT INTO requests (title,detail,priority,status) VALUES (?,?,?,?)",(title,detail,priority,"To assess"))
        db.commit()
        return {"id":cur.lastrowid,"title":title}

def update_request(request_id,status):
    if status not in ("To assess","Feasible","Needs data","Not feasible","Delivered"):raise ValueError("Invalid feasibility status")
    with LOCK,closing(connect()) as db:
        cur=db.execute("UPDATE requests SET status=? WHERE id=?",(status,request_id))
        if not cur.rowcount:raise LookupError("Request not found")
        db.commit()
    return {"id":request_id,"status":status}

def export_csv(site="All"):
    output=io.StringIO()
    writer=csv.DictWriter(output,fieldnames=["aircraft_id","site","family","planned_delivery","inspection_count","finding_count","open_findings","high_open","overdue_actions"])
    writer.writeheader()
    writer.writerows(summary(site))
    return output.getvalue().encode()

class Handler(BaseHTTPRequestHandler):
    def send(self,code,payload,content_type="application/json",extra=None):
        body=payload if isinstance(payload,bytes) else json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type",content_type)
        self.send_header("Content-Length",str(len(body)))
        self.send_header("Cache-Control","no-store")
        self.send_header("X-Content-Type-Options","nosniff")
        for k,v in (extra or {}).items():self.send_header(k,v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url=urlparse(self.path)
        path=url.path
        site=parse_qs(url.query).get("site",["All"])[0]
        if site not in ("All","Hamburg","Toulouse","Mobile","Tianjin"):
            return self.send(400,{"error":"Invalid site"})
        if path=="/api/analytics":return self.send(200,analytics(site))
        if path=="/api/requests":return self.send(200,feasibility())
        if path.startswith("/api/aircraft/"):
            result=aircraft_detail(path.removeprefix("/api/aircraft/"))
            return self.send(200,result) if result else self.send(404,{"error":"Aircraft not found"})
        if path=="/api/export":return self.send(200,export_csv(site),"text/csv; charset=utf-8",{"Content-Disposition":'attachment; filename="aircraft_quality_summary.csv"'})
        files={"/":"index.html","/app.js":"app.js","/style.css":"style.css"}
        if path in files:
            typ="text/html; charset=utf-8" if path=="/" else ("text/javascript; charset=utf-8" if path.endswith(".js") else "text/css; charset=utf-8")
            return self.send(200,(PUBLIC/files[path]).read_bytes(),typ)
        return self.send(404,{"error":"Not found"})

    def do_POST(self):
        try:
            length=int(self.headers.get("Content-Length","0"))
            if length<1 or length>10000:raise ValueError("Invalid request length")
            data=json.loads(self.rfile.read(length))
            if not isinstance(data,dict):raise ValueError("Expected JSON object")
            path=urlparse(self.path).path
            if path.startswith("/api/actions/"):result=update_action(path.split("/")[-1],data.get("status"))
            elif path.startswith("/api/findings/"):result=update_finding(path.split("/")[-1],data.get("status"))
            elif path=="/api/requests":result=add_request(data)
            elif path.startswith("/api/requests/"):result=update_request(int(path.split("/")[-1]),data.get("status"))
            else:return self.send(404,{"error":"Not found"})
            self.send(200,result)
        except (ValueError,KeyError,TypeError,json.JSONDecodeError) as exc:self.send(400,{"error":str(exc)})
        except LookupError as exc:self.send(404,{"error":str(exc)})

if __name__=="__main__":
    init_db()
    port=int(os.environ.get("PORT","8501"))
    print(f"Quality Control Tower: http://127.0.0.1:{port}")
    ThreadingHTTPServer(("127.0.0.1",port),Handler).serve_forever()
