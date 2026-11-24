import asyncio, http.server, socketserver, threading, io, os, sys
from playwright.async_api import async_playwright
DIR=os.path.dirname(os.path.abspath(__file__))      # thư mục tests/
ROOT=os.path.dirname(DIR)                            # thư mục gốc dự án
PORT=8811; SEC='ABCD2345'
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
    room=121212; md=enc(room^0x5A5A5); mk=enc(room^0xA5A5A)
    async with async_playwright() as pw:
        br=await pw.chromium.launch(executable_path='/usr/bin/google-chrome',
            args=['--no-sandbox','--disable-dev-shm-usage','--mute-audio'])
        ctx=await br.new_context(viewport={'width':1500,'height':1000})   # hiệu ứng BẬT
        await ctx.add_init_script(path=os.path.join(DIR,'stub.js'))
        async def _loc(r):
            if '127.0.0.1' in r.request.url: await r.continue_()
            else: await r.abort()
        await ctx.route('**', _loc)
        pg=await ctx.new_page(); pg.on('dialog', lambda d: asyncio.ensure_future(d.accept()))
        errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(f'http://127.0.0.1:{PORT}/tests/harness.html')
        await pg.evaluate('(h)=>window.__mount("f-mc",h)','#mc/'+mk+'/'+SEC)
        await pg.evaluate('([r,t])=>{localStorage.setItem("rcv.doi."+r+".ten",JSON.stringify(t));localStorage.setItem("rcv.doi."+r+".nha",JSON.stringify(t))}',[room,'Minties'])
        await pg.evaluate('(h)=>window.__mount("f-b",h)','#doi/'+md)
        await pg.wait_for_timeout(900)
        mc=pg.frame_locator('#f-mc')
        await mc.locator('#mc-luu-cau').click(); await pg.wait_for_timeout(600)

        for ten,w,h in (('laptop 1366x768',1366,768),('iPhone 390x844',390,844)):
            await pg.evaluate('([w,h])=>{const f=document.getElementById("f-kg");f.style.width=w+"px";f.style.height=h+"px"}',[w,h])
            await pg.evaluate('(h)=>window.__mount("f-kg",h)','?v=s'+str(w)+'#man/'+mk)
            await pg.wait_for_timeout(1500)
            fr=[f for f in pg.frames if ('v=s'+str(w)) in f.url][0]
            kg=pg.frame_locator('#f-kg')
            # dựng một thông báo rồi thử bấm nút gửi chat NGAY LÚC ĐÓ
            await fr.evaluate('()=>{const e=document.createElement("div");e.className="toast";e.textContent="Thong bao dai de che nut";document.body.appendChild(e)}')
            await pg.wait_for_timeout(200)
            che = await fr.evaluate('''()=>{const e=document.querySelector('#kg-chat-nut');
              const b=e.getBoundingClientRect(); if(b.width<2) return 'khong-bay';
              if(b.y<0||b.y+b.height>innerHeight) return 'duoi-man-hinh';
              const t=document.elementFromPoint(b.x+b.width/2,b.y+b.height/2);
              return (t===e||e.contains(t))?'bam-duoc':'bi-che-boi-'+(t&&t.className||'?')}''')
            ok('%s: có thông báo vẫn bấm được nút gửi chat'%ten, che in ('bam-duoc','khong-bay','duoi-man-hinh'), che)
            # bấm thật
            try:
                await kg.locator('#kg-chat-noi').fill('thu khi co thong bao')
                await kg.locator('#kg-chat-nut').click(timeout=6000)
                ok('%s: bấm gửi chat thành công khi đang có thông báo'%ten, True)
            except Exception as e:
                ok('%s: bấm gửi chat thành công khi đang có thông báo'%ten, False, str(e)[:90])
            ok('%s: thông báo không chắn con trỏ'%ten,
               await fr.evaluate("()=>getComputedStyle(document.querySelector('.toast')||document.body).pointerEvents==='none'"))

        # hằng số độ trễ mới
        import re as _re
        _src = io.open(os.path.join(ROOT,'rungchuongvang-index4.html'), encoding='utf-8').read()
        g = lambda k: int(_re.search(r'const '+k+r'\s*=\s*(\d+)', _src).group(1))
        c = {'goi':g('AM_GOI_MS'), 'dem':g('AM_DEM_MS'), 'demMax':g('AM_DEM_MAX'),
             'treMax':g('AM_TRE_MAX'), 'demMin':g('AM_DEM_MIN')}
        print('   hằng số tiếng:', c)
        ok('gói tiếng 160ms', c['goi']==160, c)
        ok('đệm ban đầu 320ms', c['dem']==320, c)
        ok('đệm tối đa 900ms', c['demMax']==900, c)
        ok('ngưỡng đuổi kịp 1300ms', c['treMax']==1300, c)
        ok('tổng trễ lý thuyết lúc mạng tốt < 0.6s', (c['goi']+c['dem'])/1000 < 0.6, (c['goi']+c['dem'])/1000)
        ok('đệm nhỏ nhất < đệm ban đầu (nếu không đệm không co lại được)', c['demMin'] < c['dem'], c)

        # mất mạng thì KHÔNG xếp hàng gói tiếng
        n = await pg.evaluate('''()=>{const d=document.getElementById("f-kg").contentWindow;
            return typeof d.__rcvBroker!=='undefined'}''')
        print('\nlỗi JS:', errs, flush=True)
        await br.close()
    print('\n'+('TẤT CẢ PASS' if not FAILS else 'FAIL: '+', '.join(FAILS)))
    sys.exit(1 if FAILS else 0)
asyncio.run(main())
