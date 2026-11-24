import asyncio, http.server, socketserver, threading, os, sys
from playwright.async_api import async_playwright
DIR=os.path.dirname(os.path.abspath(__file__))      # thư mục tests/
ROOT=os.path.dirname(DIR)                            # thư mục gốc dự án
PORT=8775; SEC='ABCD2345'
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
    room=676767; md=enc(room^0x5A5A5); mk=enc(room^0xA5A5A)
    async with async_playwright() as pw:
        br=await pw.chromium.launch(executable_path='/usr/bin/google-chrome',
            args=['--no-sandbox','--disable-dev-shm-usage','--mute-audio'])
        ctx=await br.new_context(reduced_motion='reduce', viewport={'width':1600,'height':1100})
        await ctx.add_init_script(path=os.path.join(DIR,'stub.js'))
        async def _loc(route):
            if '127.0.0.1' in route.request.url: await route.continue_()
            else: await route.abort()
        await ctx.route('**', _loc)
        pg=await ctx.new_page()
        errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('dialog', lambda d: asyncio.ensure_future(d.accept()))
        await pg.goto(f'http://127.0.0.1:{PORT}/tests/harness.html')
        await pg.evaluate('(h)=>window.__mount("f-mc",h)','#mc/'+mk+'/'+SEC)
        for fid,t in (('f-a','Minties'),('f-b','Chạc Chíp')):
            await pg.evaluate('([r,t])=>{localStorage.setItem("rcv.doi."+r+".ten",JSON.stringify(t));localStorage.setItem("rcv.doi."+r+".nha",JSON.stringify(t))}',[room,t])
            await pg.evaluate('([i,h])=>window.__mount(i,h)',[fid,'#doi/'+md])
        await pg.evaluate('(h)=>window.__mount("f-kg",h)','#man/'+mk)
        await pg.wait_for_timeout(1500)
        mc=pg.frame_locator('#f-mc'); ta=pg.frame_locator('#f-a'); tb=pg.frame_locator('#f-b'); kg=pg.frame_locator('#f-kg')
        ok('không có lỗi JS lúc khởi động', not errs, errs)

        # --- màn khán giả trên laptop: vẫn gọn trong 1 khung, không cuộn ---
        await pg.evaluate('()=>{const f=document.getElementById("f-kg");f.style.width="1280px";f.style.height="800px"}')
        await pg.evaluate('(h)=>window.__mount("f-kg",h)','?v=d1#man/'+mk)
        await pg.wait_for_timeout(1200)
        sc=await pg.evaluate('''()=>{const d=document.getElementById("f-kg").contentWindow;
            const e=d.document.documentElement; return [e.scrollHeight, d.innerHeight, e.scrollWidth, d.innerWidth]}''')
        ok('Khán giả/laptop 1280x800: không cuộn dọc', sc[0]<=sc[1]+2, sc)
        ok('Khán giả/laptop 1280x800: không cuộn ngang', sc[2]<=sc[3]+1, sc)

        # --- vòng chơi: ra câu hỏi, rung chuông, trả lời đúng ---
        await mc.locator('#mc-luu-cau').click(); await pg.wait_for_timeout(500)
        await mc.locator('#mc-bat-dau').click(); await pg.wait_for_timeout(5200)
        await ta.locator('#doi-chuong').click(); await pg.wait_for_timeout(700)
        ok('đội rung được chuông và được mời trả lời', (await ta.locator('#doi-chuong-chu').inner_text()) in ('ĐÃ RUNG','MỜI BẠN TRẢ LỜI!') or 'RUNG' in (await ta.locator('#doi-chuong-chu').inner_text()),
           await ta.locator('#doi-chuong-chu').inner_text())
        # đội chọn đáp án
        da = ta.locator('#doi-dap-an .da')
        n = await da.count()
        ok('đội thấy 4 đáp án', n==4, n)
        await da.nth(0).click(); await pg.wait_for_timeout(600)

        # --- Top 5 vẫn vẽ trong lúc chơi ---
        ok('Top 5 còn vẽ khi đang chơi', await ta.locator('#doi-xh .xh-hang').count()==2,
           await ta.locator('#doi-xh .xh-hang').count())

        # --- chat đội -> khán giả ---
        await ta.locator('#doi-chat-noi').fill('xin chao moi nguoi')
        await ta.locator('#doi-chat-nut').click(); await pg.wait_for_timeout(800)
        ok('chat từ đội sang màn khán giả', 'xin chao moi nguoi' in (await kg.locator('#kg-chat').inner_text()))

        # --- buff luck: khán giả chọn nhà, QR hiện (không có ảnh vì chặn mạng) ---
        await kg.locator('#kg-bl-nha').select_option(label='Minties')
        await pg.wait_for_timeout(500)
        ok('Buff Luck: chọn nhà xong khung QR có nội dung',
           len((await kg.locator('#kg-bl-qr').inner_text()).strip())>0 or await kg.locator('#kg-bl-qr img').count()>0)

        # --- link cố định vẫn phát ---
        ok('tin dangchoi vẫn còn', 'rcvang/dangchoi' in (await pg.evaluate('()=>Object.keys(window.__rcvBroker.retained)')))

        print('\nlỗi JS:', errs, flush=True)
        await br.close()
    print('\n'+('TẤT CẢ PASS' if not FAILS else 'FAIL: '+', '.join(FAILS)))
    sys.exit(1 if FAILS else 0)
asyncio.run(main())
