# holiday packages 13-17 Nov 2026 (4 nights); Bangkok and Kuala Lumpur 13-18 Nov (the Emirates flight lands the next day)
cd /home/user/CPI-Web-Scarping/scripts/oneoff/dnata
R=runs_13_20
CHECKIN=2026-11-13 CHECKOUT=2026-11-17 python3 dnata_packages.py $R/targets_main.json $R/pkg_main.json; echo MAIN_DONE
CHECKIN=2026-11-13 CHECKOUT=2026-11-18 python3 dnata_packages.py $R/targets_late.json $R/pkg_late.json; echo LATE_DONE
CHECKIN=2026-11-13 CHECKOUT=2026-11-17 python3 dnata_packages.py $R/targets_retry.json $R/pkg_retry.json; echo RETRY_DONE
