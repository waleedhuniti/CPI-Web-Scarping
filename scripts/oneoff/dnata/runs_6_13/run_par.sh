cd /home/user/CPI-Web-Scarping/scripts/oneoff/dnata
R=runs_6_13
CHECKIN=2026-11-06 CHECKOUT=2026-11-11 NIGHTS=4 SHOTDIR=$R/shots python3 shots.py $R/pkg_late.json $R/shots_late.json > $R/late_shots.log 2>&1 &
CHECKIN=2026-11-06 CHECKOUT=2026-11-10 NIGHTS=4 SHOTDIR=$R/shots python3 shots_next.py $R/pkg_maldives.json $R/shots_maldives.json > $R/maldives.log 2>&1 &
wait; echo PAR_DONE
