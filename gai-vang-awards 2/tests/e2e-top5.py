import asyncio, http.server, socketserver, threading, os, sys
from playwright.async_api import async_playwright
DIR=os.path.dirname(os.path.abspath(__file__))      # thư mục tests/
ROOT=os.path.dirname(DIR)                            # thư mục gốc dự án
PORT=8779; SEC='ABCD2345'
class S(socketserver.ThreadingMixIn, http.server.HTTPServer): daemon_threads=True
class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self,*a,**k): super().__init__(*a,directory=ROOT,**k)
    def log_message(self,*a): pass
threading.Thread(target=lambda: S(('127.0.0.1',PORT),H).serve_forever(),daemon=True).start()
FAILS=[]
def ok(n,c,extra=''):
    print(('PASS  ' if c else 'FAIL  ')+n+(('   << '+str(extra)) if (not c and extra!='') else ''),flush=True)
    if not c: FAILS.append(n)
AL='0123456789ABCDEFGHJKMNPQRSTVWXYZ'
def enc(n):
    s=''
    for _ in range(4): s=AL[n&31]+s; n>>=5
    return s
async def main():
    room=272727; md=enc(room^0x5A5A5); mk=enc(room^0xA5A5A)
    async with async_playwright() as pw:
        br=await pw.chromium.launch(executable_path='/usr/bin/google-chrome',
            args=['--no-sandbox','--disable-dev-shm-usage','--mute-audio'])
        ctx=await br.new_context(reduced_motion='reduce', viewport={'width':1500,'height':1100})
        await ctx.add_init_script(path=os.path.join(DIR,'stub.js'))
        async def _loc(route):
            if '127.0.0.1' in route.request.url: await route.continue_()
            else: await route.abort()
        await ctx.route('**', _loc)
        pg=await ctx.new_page(); pg.on('dialog', lambda d: asyncio.ensure_future(d.accept()))
        errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(f'http://127.0.0.1:{PORT}/tests/harness.html')
        await pg.evaluate('(h)=>window.__mount("f-mc",h)','#mc/'+mk+'/'+SEC)
        await pg.wait_for_timeout(700)
        # 7 đội: f-a là đội của mình (hạng chót) + 6 đội khác qua iframe thêm
        tens=['Minties','Chạc Chíp','LASIDO','TIU','TRẠM WILL','CMBF','Cheng']
        for i,t in enumerate(tens):
            fid='f-t%d'%i
            await pg.evaluate('(i)=>window.__addFrame(i)',fid)
            await pg.evaluate('([r,t])=>{localStorage.setItem("rcv.doi."+r+".ten",JSON.stringify(t));localStorage.setItem("rcv.doi."+r+".nha",JSON.stringify(t))}',[room,t])
            await pg.evaluate('([i,h])=>window.__mount(i,h)',[fid,'?v='+str(i)+'#doi/'+md])
        await pg.wait_for_timeout(2000)
        mc=pg.frame_locator('#f-mc')
        await mc.locator('#mc-luu-cau').click(); await pg.wait_for_timeout(600)
        # cho mỗi đội một số điểm khác nhau bằng cách cộng câu đúng thủ công không có -> dùng xếp hạng mặc định
        so = await pg.evaluate('()=>document.getElementById("f-t6").contentWindow.document.querySelectorAll("#doi-xh .xh-hang").length')
        ok('7 đội: Top 5 chỉ vẽ 5 hàng + hàng của mình', so in (5,6), so)
        cach = await pg.evaluate('()=>document.getElementById("f-t6").contentWindow.document.querySelectorAll("#doi-xh .xh-cach").length')
        toi = await pg.evaluate('()=>document.getElementById("f-t6").contentWindow.document.querySelectorAll("#doi-xh .xh-hang.toi").length')
        ok('7 đội: luôn có đúng 1 hàng của chính mình', toi==1, toi)
        ok('7 đội: nếu ngoài top 5 thì có dấu ··· ngăn cách', (so==6 and cach==1) or (so==5 and cach==0), (so,cach))
        # khổ laptop 1280x800: cột trái không tràn khỏi khung
        await pg.evaluate('()=>{const f=document.getElementById("f-t6");f.style.width="1280px";f.style.height="800px"}')
        await pg.evaluate('(h)=>window.__mount("f-t6",h)','?v=zz#doi/'+md)
        await pg.wait_for_timeout(1500)
        r = await pg.evaluate('''()=>{const d=document.getElementById("f-t6").contentWindow, q=s=>d.document.querySelector(s);
            const c=q("#doi-chat-the").getBoundingClientRect(), x=q("#doi-xh-the").getBoundingClientRect();
            const e=q("#doi-xh");
            return {chatDay:Math.round(c.bottom), man:d.innerHeight, top5:Math.round(x.height),
                    hienRow:Math.round(e.clientHeight), canRow:e.scrollHeight,
                    docCuon:d.document.documentElement.scrollHeight<=d.innerHeight+2}}''')
        ok('Laptop 1280x800: chat không bị đẩy khỏi màn hình', r['chatDay']<=r['man']+2, r)
        ok('Laptop 1280x800: trang không cuộn dọc', r['docCuon'], r)
        ok('Laptop 1280x800: Top 5 thấy ít nhất 2 hàng, phần dư cuộn được', r['hienRow']>=70, r)
        await pg.locator('#f-t6').screenshot(path=os.path.join(ROOT,'anh-doi-laptop.png'))
        await pg.evaluate('()=>{const f=document.getElementById("f-t6");f.style.width="390px";f.style.height="1500px"}')
        await pg.evaluate('(h)=>window.__mount("f-t6",h)','?v=yy#doi/'+md)
        await pg.wait_for_timeout(1500)
        await pg.locator('#f-t6').screenshot(path=os.path.join(ROOT,'anh-doi-dienthoai.png'))
        print('\nlỗi JS:', errs, flush=True)
        await br.close()
    print('\n'+('TẤT CẢ PASS' if not FAILS else 'FAIL: '+', '.join(FAILS)))
    sys.exit(1 if FAILS else 0)
asyncio.run(main())
