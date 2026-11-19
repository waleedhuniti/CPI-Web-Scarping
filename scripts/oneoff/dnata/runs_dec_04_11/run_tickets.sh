# air tickets: out 4 Dec, back 11 Dec 2026, each airline from its own site, one after another.
# Emirates: run_ek_windows.cmd on a PC (emirates.com answers 403 from cloud servers). PIA, Air India, Turkish: manual.
cd /home/user/CPI-Web-Scarping/scripts/oneoff/dnata
R=runs_dec_04_11
xvfb-run -a python3 fz_full.py 20261204 20261211 $R/fz_res.json DEL RUH KHI CMB IST ALY AMM; echo FZ_DONE
xvfb-run -a python3 air_saudia.py 2026-12-04 2026-12-11 $R/air_saudia_res.json RUH; echo SV_DONE
xvfb-run -a python3 air_egyptair.py 20261204 20261211 $R/air_egyptair_res.json; echo MS_DONE
xvfb-run -a python3 air_rj.py 2026-12-04 2026-12-11 $R/air_rj_res.json AMM; echo RJ_DONE
xvfb-run -a python3 air_ba.py 2026-12-04 2026-12-11 $R/air_ba_res.json; echo TICKETS_ALL_DONE
