import asyncio, http.server, socketserver, threading, os, sys
from playwright.async_api import async_playwright
DIR=os.path.dirname(os.path.abspath(__file__))      # thư mục tests/
ROOT=os.path.dirname(DIR)                            # thư mục gốc dự án
PORT=8823; SEC='ABCD2345'
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
    room=141414; md=enc(room^0x5A5A5); mk=enc(room^0xA5A5A)
    async with async_playwright() as pw:
        br=await pw.chromium.launch(executable_path='/usr/bin/google-chrome',
            args=['--no-sandbox','--disable-dev-shm-usage','--mute-audio',
                  '--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream'])
        ctx=await br.new_context(viewport={'width':1500,'height':1000}, permissions=['microphone'])
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
        await pg.wait_for_timeout(1000)
        mc=pg.frame_locator('#f-mc')
        await mc.locator('#mc-luu-cau').click(); await pg.wait_for_timeout(500)
        await mc.locator('#mc-th-vao').click(); await pg.wait_for_timeout(2500)

        async def dem(ai, giay=3):
            await pg.evaluate('()=>{window.__rcvBroker.log.length=0}')
            await pg.wait_for_timeout(int(giay*1000))
            return await pg.evaluate('(ai)=>window.__rcvBroker.log.filter(m=>m.topic.endsWith("/am/"+ai)).length', ai)

        # ===== A) KHOÁ TRƯỚC khi đội vào phòng thoại =====
        await mc.locator('#mc-th-khoa-het').click(); await pg.wait_for_timeout(800)
        await pg.evaluate('(h)=>window.__mount("f-a",h)','#doi/'+md)
        await pg.wait_for_timeout(4000)
        ta=pg.frame_locator('#f-a')
        doiId = await pg.evaluate('()=>JSON.parse(localStorage.getItem("rcv.doi.%d.id.minties")||"null")'%room)
        print('   id đội:', doiId, '| nút mic:', await ta.locator('#doi-th-nut').inner_text())
        n=await dem(doiId)
        ok('A) khoá TRƯỚC khi đội vào: đội không gửi tiếng', n==0, 'gửi %d gói'%n)

        # ===== B) mở lại, đội nói, rồi đội TẢI LẠI TRANG trong lúc bị khoá =====
        await mc.locator('#mc-th-mo-het').click(); await pg.wait_for_timeout(1200)
        if 'bấm để nói' in (await ta.locator('#doi-th-nut').inner_text()):
            await ta.locator('#doi-th-nut').click(); await pg.wait_for_timeout(1500)
        n=await dem(doiId); ok('B0) mở hết: đội gửi được tiếng', n>0, n)
        await mc.locator('#mc-th-khoa-het').click(); await pg.wait_for_timeout(1000)
        await pg.evaluate('(h)=>window.__mount("f-a",h)','?v=b#doi/'+md)   # đội tải lại trang
        await pg.wait_for_timeout(5000)
        print('   sau khi đội tải lại, nút mic:', await ta.locator('#doi-th-nut').inner_text())
        n=await dem(doiId)
        ok('B) đội tải lại trang trong lúc bị khoá: vẫn im', n==0, 'gửi %d gói'%n)

        # ===== C) kiểu thoại NGANG HÀNG (WebRTC) =====
        await mc.locator('#mc-th-mo-het').click(); await pg.wait_for_timeout(800)
        try:
            await mc.locator('#mc-th-kieu').select_option('ngang')
        except Exception as e:
            print('   (không chọn được kiểu ngang hàng:', str(e)[:70], ')')
        await pg.wait_for_timeout(3500)
        kieu = await pg.evaluate('()=>JSON.parse(localStorage.getItem("rcv.mc.%d.state")||"{}").kieuThoai'%room)
        print('   kiểu thoại hiện tại:', kieu)
        if kieu=='ngang':
            await pg.wait_for_timeout(3000)
            print('   nút mic của đội:', await ta.locator('#doi-th-nut').inner_text())
            tr = await pg.evaluate('''(id)=>{const d=document.getElementById("f-a").contentWindow;
                return 'khong-doc-duoc'}''', doiId)
            await mc.locator('#mc-th-khoa-het').click(); await pg.wait_for_timeout(1500)
            txt = await ta.locator('#doi-th-nut').inner_text()
            ok('C) ngang hàng: đội thấy chữ bị khoá', 'Chờ quản trò' in txt, txt)
        print('\nlỗi JS:', errs, flush=True)
        await br.close()
    print('\n'+('TẤT CẢ PASS' if not FAILS else 'FAIL: '+', '.join(FAILS)))
    sys.exit(1 if FAILS else 0)
asyncio.run(main())
