# screenshots / page totals for 13-17 Nov (Bangkok, Kuala Lumpur 13-18); Maldives through the extras page (mandatory transfer)
cd /home/user/CPI-Web-Scarping/scripts/oneoff/dnata
R=runs_13_20
until grep -q RETRY_DONE $R/pkg.log; do sleep 20; done
python3 - <<'PY'
import json
R='runs_13_20'
m=json.load(open(f'{R}/pkg_main.json')); r=json.load(open(f'{R}/pkg_retry.json'))
mal={k:v for k,v in {**m,**{k:v for k,v in r.items() if v.get('total')}}.items() if v.get('city')=='Maldives' and v.get('total')}
json.dump({k:v for k,v in m.items() if v.get('city')!='Maldives'},open(f'{R}/pkg_main_nomal.json','w'),ensure_ascii=False,indent=1)
json.dump({k:v for k,v in r.items() if v.get('city')!='Maldives'},open(f'{R}/pkg_retry_nomal.json','w'),ensure_ascii=False,indent=1)
json.dump(mal,open(f'{R}/pkg_maldives.json','w'),ensure_ascii=False,indent=1)
print('maldives rows',list(mal))
PY
CHECKIN=2026-11-13 CHECKOUT=2026-11-17 NIGHTS=4 SHOTDIR=$R/shots python3 shots.py $R/pkg_main_nomal.json $R/shots_main.json > $R/shots_main.log 2>&1 &
CHECKIN=2026-11-13 CHECKOUT=2026-11-18 NIGHTS=4 SHOTDIR=$R/shots python3 shots.py $R/pkg_late.json $R/shots_late.json > $R/shots_late.log 2>&1 &
CHECKIN=2026-11-13 CHECKOUT=2026-11-17 NIGHTS=4 SHOTDIR=$R/shots python3 shots_next.py $R/pkg_maldives.json $R/shots_maldives.json > $R/maldives.log 2>&1 &
wait
CHECKIN=2026-11-13 CHECKOUT=2026-11-17 NIGHTS=4 SHOTDIR=$R/shots python3 shots.py $R/pkg_retry_nomal.json $R/shots_retry.json > $R/shots_retry.log 2>&1
echo SHOTS_ALL_DONE
