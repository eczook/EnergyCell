import argparse, html, json, pathlib, re, http.server, socketserver, threading, webbrowser

class ECError(Exception): pass

def lex(source):
    out=[]; i=0; line=1; col=1
    while i < len(source):
        ch=source[i]
        if ch.isspace():
            if ch == "\n": line += 1; col = 1
            else: col += 1
            i += 1; continue
        if ch == "#":
            while i < len(source) and source[i] != "\n": i += 1; col += 1
            continue
        start_line, start_col = line, col
        if ch in "{}:;":
            out.append((ch,ch,line,col)); i += 1; col += 1; continue
        if ch in ("\"", "'"):
            quote=ch; i += 1; col += 1; chars=[]
            while i < len(source) and source[i] != quote:
                cur=source[i]
                if cur == "\\":
                    i += 1; col += 1
                    if i >= len(source): raise ECError(f"{start_line}:{start_col}: unfinished string escape")
                    esc=source[i]; chars.append({"n":"\n","t":"\t","r":"\r"}.get(esc,esc))
                else:
                    chars.append(cur)
                    if cur == "\n": line += 1; col = 0
                i += 1; col += 1
            if i >= len(source): raise ECError(f"{start_line}:{start_col}: unterminated string")
            i += 1; col += 1
            out.append(("STRING", "".join(chars), start_line, start_col)); continue
        if ch.isalpha() or ch == "_":
            j=i
            while i < len(source) and (source[i].isalnum() or source[i] in "_-"):
                i += 1; col += 1
            out.append(("IDENT",source[j:i],start_line,start_col)); continue
        raise ECError(f"{line}:{col}: unexpected character {ch!r}")
    out.append(("EOF","",line,col)); return out

class Parser:
    def __init__(self, source): self.t=lex(source); self.i=0
    @property
    def cur(self): return self.t[self.i]
    def take(self, kind=None, value=None):
        t=self.cur
        if kind and t[0]!=kind or value is not None and t[1]!=value:
            raise ECError(f"{t[2]}:{t[3]}: expected {value or kind}")
        if t[0]!="EOF": self.i+=1
        return t
    def sep(self):
        while self.cur[0]==";": self.take(";")
    def string(self): return self.take("STRING")[1]
    def block(self): self.take("{")
    def elements(self, closing=True):
        nodes=[]
        if closing: self.block()
        while self.cur[0]!="}" and self.cur[0]!="EOF":
            self.sep()
            if self.cur[0] in ("}","EOF"): break
            word=self.take("IDENT")[1]
            if word in ("heading","text"): nodes.append({"type":word,"value":self.string()})
            elif word=="container": nodes.append({"type":"container","children":self.elements()})
            elif word=="button":
                label=self.string(); self.block()
                self.take("IDENT","on"); self.take("IDENT","click"); self.block()
                self.take("IDENT","show"); message=self.string(); self.sep()
                self.take("}"); self.sep(); self.take("}")
                nodes.append({"type":"button","value":label,"message":message})
            else: raise ECError(f"{self.cur[2]}:{self.cur[3]}: unknown element {word!r}")
            self.sep()
        if closing: self.take("}")
        return nodes
    def parse(self):
        self.take("IDENT","page"); self.block()
        tree={"title":"EnergyCell page","styles":{},"children":[]}; seen=False
        while self.cur[0]!="}" and self.cur[0]!="EOF":
            self.sep()
            if self.cur[0] in ("}","EOF"): break
            word=self.take("IDENT")[1]
            if word=="title":
                if seen: raise ECError("page can only have one title")
                tree["title"]=self.string(); seen=True
            elif word=="style":
                self.block()
                while self.cur[0]!="}" and self.cur[0]!="EOF":
                    self.sep()
                    if self.cur[0] in ("}","EOF"): break
                    key=self.take("IDENT")[1]
                    if key not in ("background","color","font"): raise ECError(f"unknown style property {key!r}")
                    self.take(":"); tree["styles"][key]=self.string(); self.sep()
                self.take("}")
            elif word in ("heading","text"): tree["children"].append({"type":word,"value":self.string()})
            elif word=="container": tree["children"].append({"type":"container","children":self.elements()})
            elif word=="button":
                label=self.string(); self.block(); self.take("IDENT","on"); self.take("IDENT","click"); self.block()
                self.take("IDENT","show"); msg=self.string(); self.sep(); self.take("}"); self.sep(); self.take("}")
                tree["children"].append({"type":"button","value":label,"message":msg})
            else: raise ECError(f"unknown page item {word!r}")
            self.sep()
        self.take("}"); self.take("EOF"); return tree

def compile_ec(source):
    t=Parser(source).parse()
    styles={"background":"background-color","color":"color","font":"font-family"}
    css=["body{margin:0;padding:2rem;line-height:1.5;font-family:Arial,sans-serif}",".ec-container{max-width:900px;margin:0 auto}",".ec-button{padding:.65rem 1rem;border:0;border-radius:6px;cursor:pointer;font:inherit}"]
    for k,v in t["styles"].items(): css.append(f"body{{{styles[k]}:{v};}}")
    scripts=[]; count=[0]
    def render(nodes):
        out=[]
        for n in nodes:
            k=n["type"]; v=html.escape(n.get("value",""),quote=True)
            if k=="heading": out.append(f"<h1>{v}</h1>")
            elif k=="text": out.append(f"<p>{v}</p>")
            elif k=="container": out.append('<section class="ec-container">'+render(n["children"])+"</section>")
            elif k=="button":
                count[0]+=1; ident=f"ec-button-{count[0]}"
                out.append(f'<button class="ec-button" id="{ident}" type="button">{v}</button>')
                scripts.append(f"document.getElementById({json.dumps(ident)}).addEventListener('click',()=>window.alert({json.dumps(n['message'])}));")
        return "\\n".join(out)
    body=render(t["children"])
    return f'<!doctype html>\\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(t["title"])}</title><style>{"".join(css)}</style></head><body>{body}<script>{"".join(scripts)}</script></body></html>'

def main():
    p=argparse.ArgumentParser(prog="ec",description="EnergyCell 0.1 prototype")
    sub=p.add_subparsers(dest="cmd",required=True)
    for name in ("check","build","run"):
        q=sub.add_parser(name); q.add_argument("source")
        if name=="build": q.add_argument("-o","--output")
        if name=="run": q.add_argument("--port",type=int,default=8000); q.add_argument("--no-browser",action="store_true")
    a=p.parse_args()
    try:
        source=pathlib.Path(a.source).read_text(encoding="utf-8")
        output=compile_ec(source)
        if a.cmd=="check": print(f"OK: {a.source}"); return 0
        if a.cmd=="build":
            dest=pathlib.Path(a.output or pathlib.Path(a.source).with_suffix(".html")); dest.write_text(output,encoding="utf-8"); print(f"Built {dest}"); return 0
        handler=type("Handler",(http.server.BaseHTTPRequestHandler,),{"do_GET":lambda self:(self.send_response(200),self.send_header("Content-Type","text/html; charset=utf-8"),self.end_headers(),self.wfile.write(output.encode())),"log_message":lambda *args:None})
        with socketserver.TCPServer(("127.0.0.1",a.port),handler) as server:
            url=f"http://127.0.0.1:{a.port}/"; print(f"Preview: {url} (Ctrl+C to stop)")
            if not a.no_browser: threading.Timer(.5,lambda:webbrowser.open(url)).start()
            try: server.serve_forever()
            except KeyboardInterrupt: print("\\nStopped.")
    except (OSError,ECError) as e:
        print(f"EnergyCell error: {e}"); return 1
    return 0
if __name__=="__main__": raise SystemExit(main())
