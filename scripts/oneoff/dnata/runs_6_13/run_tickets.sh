# air tickets: out 6 Nov, back 13 Nov 2026, each airline from its own site
cd /home/user/CPI-Web-Scarping/scripts/oneoff/dnata
R=runs_6_13
xvfb-run -a python3 fz_full.py 20261106 20261113 $R/fz_res.json DEL RUH KHI CMB IST ALY AMM; echo FZ_DONE
xvfb-run -a python3 air_saudia.py 2026-11-06 2026-11-13 $R/air_saudia_res.json RUH; echo SV_DONE
xvfb-run -a python3 air_egyptair.py 20261106 20261113 $R/air_egyptair_res.json; echo MS_DONE
xvfb-run -a python3 air_rj.py 2026-11-06 2026-11-13 $R/air_rj_res.json AMM; echo RJ_DONE
xvfb-run -a python3 air_pia.py DXB ISB 2026-11-06 2026-11-13 $R/air_pia_res.json; echo PK_DONE
xvfb-run -a python3 air_ba.py 2026-11-06 2026-11-13 $R/air_ba_res.json; echo BA_DONE
