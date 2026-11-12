# holiday packages 20-24 Nov 2026 (4 nights); Bangkok and Kuala Lumpur 20-25 Nov (the Emirates flight lands the next day).
# One dnata session at a time (CLAUDE.md: never two processes against one shop).
cd /home/user/CPI-Web-Scarping/scripts/oneoff/dnata
R=runs_20_27
CHECKIN=2026-11-20 CHECKOUT=2026-11-24 python3 dnata_packages.py $R/targets_main.json $R/pkg_main.json; echo MAIN_DONE
CHECKIN=2026-11-20 CHECKOUT=2026-11-25 python3 dnata_packages.py $R/targets_late.json $R/pkg_late.json; echo LATE_DONE
python3 - <<'PY'
import json
R='runs_20_27'
m=json.load(open(f'{R}/pkg_main.json'))
json.dump({k:v for k,v in m.items() if v.get('city')!='Maldives'},open(f'{R}/pkg_main_nomal.json','w'),ensure_ascii=False,indent=1)
json.dump({k:v for k,v in m.items() if v.get('city')=='Maldives' and v.get('total')},open(f'{R}/pkg_maldives.json','w'),ensure_ascii=False,indent=1)
PY
CHECKIN=2026-11-20 CHECKOUT=2026-11-24 NIGHTS=4 SHOTDIR=$R/shots python3 shots.py $R/pkg_main_nomal.json $R/shots_main.json > $R/shots_main.log 2>&1; echo SHOTS_MAIN_DONE
CHECKIN=2026-11-20 CHECKOUT=2026-11-25 NIGHTS=4 SHOTDIR=$R/shots python3 shots.py $R/pkg_late.json $R/shots_late.json > $R/shots_late.log 2>&1; echo SHOTS_LATE_DONE
CHECKIN=2026-11-20 CHECKOUT=2026-11-24 NIGHTS=4 SHOTDIR=$R/shots python3 shots_next.py $R/pkg_maldives.json $R/shots_maldives.json > $R/maldives.log 2>&1; echo PKG_ALL_DONE
