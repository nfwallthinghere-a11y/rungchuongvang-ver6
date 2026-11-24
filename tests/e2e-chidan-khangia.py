import asyncio, http.server, socketserver, threading, os, sys
from playwright.async_api import async_playwright
DIR=os.path.dirname(os.path.abspath(__file__))      # thư mục tests/
ROOT=os.path.dirname(DIR)                            # thư mục gốc dự án
PORT=8841; SEC='ABCD2345'
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
    room=363636; md=enc(room^0x5A5A5); mk=enc(room^0xA5A5A)
    async with async_playwright() as pw:
        br=await pw.chromium.launch(executable_path='/usr/bin/google-chrome',
            args=['--no-sandbox','--disable-dev-shm-usage','--mute-audio'])
        ctx=await br.new_context(reduced_motion='reduce', viewport={'width':1500,'height':1000})
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
        await pg.frame_locator('#f-mc').locator('#mc-luu-cau').click(); await pg.wait_for_timeout(500)

        for ten,w,h in (('laptop 1366x768',1366,768),('iPhone 390x844',390,844)):
            await pg.evaluate('([w,h])=>{const f=document.getElementById("f-kg");f.style.width=w+"px";f.style.height=h+"px"}',[w,h])
            await pg.evaluate('(h)=>window.__mount("f-kg",h)','?v=c'+str(w)+'#man/'+mk)
            await pg.wait_for_timeout(1600)
            kg=pg.frame_locator('#f-kg')
            print('\n--- %s ---'%ten)
            gon = await kg.locator('#kg-bl-chidan').inner_text()
            print('   bảng Buff Luck:', gon.replace('\n',' | '))
            ok('%s: bảng Buff Luck có chỉ dẫn'%ten, len(gon.strip())>20, gon)
            ok('%s: nêu mốc 20.000đ'%ten, '20.000' in gon, gon)
            ok('%s: nêu mốc 30.000đ'%ten, '30.000' in gon, gon)
            ok('%s: nêu mốc tổng 150.000đ và 200.000đ'%ten, '150.000' in gon and '200.000' in gon, gon)
            ok('%s: chỉ dẫn nhìn thấy được'%ten, await kg.locator('#kg-bl-chidan').is_visible())

            # mở hộp thoại gửi buff -> chỉ dẫn đầy đủ
            await kg.locator('#kg-bl-gui, #kg-buff >> visible=true').first.click()
            await pg.wait_for_timeout(900)
            day = await kg.locator('#buff-chidan').inner_text()
            print('   hộp thoại:', day.replace('\n',' | ')[:200])
            ok('%s: hộp thoại có chỉ dẫn đầy đủ'%ten, '50/50' in day and 'Nhân đôi' in day
               and 'Cướp quyền' in day and 'Người thân' in day, day[:200])
            thap = day.lower()
            ok('%s: nói rõ tính theo từng đơn'%ten, 'từng đơn' in thap, day[:200])
            ok('%s: nói rõ không giới hạn số lần'%ten, 'không giới hạn' in thap, day[:200])
            ok('%s: nói rõ nhiều đơn nhỏ không cộng lại'%ten, 'không cộng lại' in day, day[:240])
            ok('%s: nói rõ đạt hết thì chạy lại'%ten, 'chạy lại' in day, day[:240])
            # ô tiền sẵn có gắn biểu tượng quyền
            tien = await kg.locator('#buff-tien').inner_text()
            print('   ô tiền sẵn:', tien.replace('\n',' · '))
            ok('%s: ô 20.000đ gắn biểu tượng 50/50'%ten, '✂️' in tien, tien)
            ok('%s: ô từ 50.000đ gắn cả hai biểu tượng'%ten, '✖️' in tien, tien)
            # lớp position:fixed trong iframe: harness không tính được toạ độ, bấm bằng JS
            await pg.evaluate('()=>document.getElementById("f-kg").contentWindow.document.getElementById("buff-dong").click()')
            await pg.wait_for_timeout(600)
            ok('%s: đóng được hộp thoại'%ten,
               await pg.evaluate('()=>document.getElementById("f-kg").contentWindow.document.getElementById("buff-lop").classList.contains("hidden")'))
            if w==390: await pg.locator('#f-kg').screenshot(path=os.path.join(DIR,'anh-chidan.png'))

        # đổi mốc ở bàn quản trò -> chỉ dẫn phải đổi theo
        mc=pg.frame_locator('#f-mc')
        o = mc.locator('#mc-moc input').first
        await o.fill('25000'); await o.press('Enter'); await pg.wait_for_timeout(1500)
        kg=pg.frame_locator('#f-kg')
        gon = await kg.locator('#kg-bl-chidan').inner_text()
        ok('quản trò đổi mốc 20k -> 25k: chỉ dẫn khán giả đổi theo', '25.000' in gon, gon)

        print('\nlỗi JS:', errs, flush=True)
        await br.close()
    print('\n'+('TẤT CẢ PASS' if not FAILS else 'FAIL: '+', '.join(FAILS)))
    sys.exit(1 if FAILS else 0)
asyncio.run(main())
