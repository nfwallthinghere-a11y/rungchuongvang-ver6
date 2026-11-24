import asyncio, http.server, socketserver, threading, os, sys
from playwright.async_api import async_playwright
DIR=os.path.dirname(os.path.abspath(__file__))      # thư mục tests/
ROOT=os.path.dirname(DIR)                            # thư mục gốc dự án
PORT=8768; SEC='ABCD2345'
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
MAN=[('iPhone SE',375,667),('iPhone 14',390,844),('Pixel 7',412,915)]

async def main():
    room=939393; md=enc(room^0x5A5A5); mk=enc(room^0xA5A5A)
    async with async_playwright() as pw:
        br=await pw.chromium.launch(executable_path='/usr/bin/google-chrome',
            args=['--no-sandbox','--disable-dev-shm-usage','--mute-audio'])
        ctx=await br.new_context(reduced_motion='reduce', viewport={'width':1400,'height':1000})
        await ctx.add_init_script(path=os.path.join(DIR,'stub.js'))
        # chặn mọi request ra ngoài (Drive, fonts): proxy môi trường chặn sẵn nên chờ rất lâu
        async def _loc(route):
            if '127.0.0.1' in route.request.url: await route.continue_()
            else: await route.abort()
        await ctx.route('**', _loc)
        pg=await ctx.new_page()
        errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('dialog', lambda d: asyncio.ensure_future(d.accept()))
        await pg.goto(f'http://127.0.0.1:{PORT}/tests/harness.html')
        await pg.evaluate('(h)=>window.__mount("f-mc",h)','#mc/'+mk+'/'+SEC)
        await pg.evaluate('([r,t])=>{localStorage.setItem("rcv.doi."+r+".ten",JSON.stringify(t));localStorage.setItem("rcv.doi."+r+".nha",JSON.stringify(t))}',[room,'Minties'])
        await pg.evaluate('(h)=>window.__mount("f-b",h)','#doi/'+md)
        await pg.wait_for_timeout(900)
        mc=pg.frame_locator('#f-mc')
        await mc.locator('#mc-luu-cau').click(); await pg.wait_for_timeout(500)
        box=lambda fid,sel: pg.evaluate('''([f,s])=>{const d=document.getElementById(f).contentWindow;
            const e=d.document.querySelector(s); if(!e) return null;
            const r=e.getBoundingClientRect(); return {t:Math.round(r.top+d.scrollY),h:Math.round(r.height)}}''',[fid,sel])

        # A) thứ tự + chiều cao khung trên 3 khổ máy
        for ten,w,h in MAN:
            await pg.evaluate('([w,h])=>{const f=document.getElementById("f-kg");f.style.width=w+"px";f.style.height=h+"px"}',[w,h])
            await pg.evaluate('(h)=>window.__mount("f-kg",h)','?v='+str(w)+'#man/'+mk)
            await pg.wait_for_timeout(1300)
            cau=await box('f-kg','#kg-khung-cau'); chat=await box('f-kg','#v-kg .chat-khung')
            buff=await box('f-kg','#kg-buff-bang'); xh=await box('f-kg','#kg-khung-xh'); bl=await box('f-kg','#kg-bxh-buff')
            ok(f'{ten}: câu hỏi -> chat -> Buff -> BXH -> BXH Buff',
               cau['t']<chat['t']<buff['t']<xh['t']<bl['t'], (cau,chat,buff,xh,bl))
            ok(f'{ten}: khung chat cao cố định <= 62vh', chat['h']<=round(h*0.62)+2, (chat['h'],round(h*0.62)))
            ok(f'{ten}: không có thanh cuộn ngang',
               await pg.evaluate('()=>{const d=document.getElementById("f-kg").contentWindow;return d.document.documentElement.scrollWidth<=d.innerWidth+1}'))

        # B) bơm chat SAU khi khán giả đã vào -> khung không giãn, cuộn bên trong
        caoTruoc = (await box('f-kg','#v-kg .chat-khung'))['h']
        for i in range(18):
            await mc.locator('#mc-chat-noi').fill('Tin thu nghiem so %d, co doi day la mot tin nhan kha dai de khung chat phai cuon chu khong duoc gian ra'%i)
            await mc.locator('#mc-chat-nut').click()
        await pg.wait_for_timeout(1000)
        caoSau = (await box('f-kg','#v-kg .chat-khung'))['h']
        ok('18 tin chat: khung chat KHÔNG cao thêm', abs(caoSau-caoTruoc)<=2, (caoTruoc,caoSau))
        scr=await pg.evaluate('''()=>{const d=document.getElementById("f-kg").contentWindow;
            const e=d.document.querySelector("#v-kg .chat-khung .chat-ds");
            return [e.scrollHeight, Math.round(e.clientHeight), Math.round(e.scrollTop)]}''')
        ok('18 tin chat: tin nhắn cuộn BÊN TRONG khung', scr[0]>scr[1]+40, scr)
        ok('18 tin chat: tự cuộn xuống tin mới nhất', scr[2]+scr[1]>=scr[0]-20, scr)
        ok('18 tin chat: trang không dài thêm quá nhiều',
           (await box('f-kg','#kg-bxh-buff'))['t'] < 2600, (await box('f-kg','#kg-bxh-buff')))
        await pg.evaluate('()=>{const f=document.getElementById("f-kg");f.style.height="1700px"}')
        await pg.wait_for_timeout(300)
        await pg.screenshot(path=os.path.join(ROOT,'kt-kg-390.png'), full_page=True)
        print('\nlỗi JS:', errs, flush=True)
        await br.close()
    print('\n'+('TẤT CẢ PASS' if not FAILS else 'FAIL: '+', '.join(FAILS)))
    sys.exit(1 if FAILS else 0)
asyncio.run(main())
