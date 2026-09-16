"""Keep all labeled card fields inside their physical A4/cutout boundaries."""
from pathlib import Path
import re
import shutil
import subprocess
import pytest
from dnd_board_game.character_creation import PLAYABLE_HERO_IDS
from dnd_board_game.physical_cards.mana_print import build_print_hero
from dnd_board_game.physical_cards.mana_print_html import FORMATS,CSS,render_hero_html


@pytest.mark.parametrize('format_id',FORMATS)
def test_labeled_cards_fit_pages_and_cutouts(tmp_path: Path,format_id: str) -> None:
    chrome=shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome:pytest.skip('Chrome required')
    pages=''.join(''.join(re.findall(r'<section class="page.*?</section>',render_hero_html(build_print_hero(h),format_id),re.S)) for h in PLAYABLE_HERO_IDS)
    script=r'''
const errors=[];
for(const card of document.querySelectorAll('[data-card-id]')){
 const end=card.lastElementChild.getBoundingClientRect().bottom;
 const limit=card.getBoundingClientRect().bottom-parseFloat(getComputedStyle(card).paddingBottom);
 if(end>limit+1)errors.push(card.dataset.cardId+': '+Math.ceil(end-limit)+'px beyond card');
}
for(const page of document.querySelectorAll('.page')){
 const footer=page.querySelector('footer').getBoundingClientRect().top;
 const children=[...page.children].filter(c=>c.tagName!=='FOOTER');
 const bottom=Math.max(...children.map(c=>c.getBoundingClientRect().bottom));
 if(bottom>footer)errors.push(page.querySelector('h1').innerText+' page '+page.dataset.page+': overlaps footer');
}
document.getElementById('result').textContent=errors.length?errors.join('; '):'PASS';
'''
    page=tmp_path/'cards.html'
    page.write_text('<meta charset="utf-8"><style>'+CSS+'</style>'+pages+'<pre id="result">PENDING</pre><script>'+script+'</script>')
    result=subprocess.run([chrome,'--headless','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-first-run',
        '--disable-background-networking',f'--user-data-dir={tmp_path/"chrome"}','--dump-dom',page.as_uri()],
        capture_output=True,text=True,timeout=25)
    assert result.returncode==0,result.stderr[-1000:]
    status=re.search(r'<pre id="result">(.*?)</pre>',result.stdout,re.S)
    assert status and status.group(1)=='PASS',status.group(1) if status else result.stdout[-1000:]
