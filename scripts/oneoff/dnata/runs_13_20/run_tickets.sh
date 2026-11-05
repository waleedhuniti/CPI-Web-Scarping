# air tickets: out 13 Nov, back 20 Nov 2026, each airline from its own site (Emirates: run_ek_windows.cmd on a PC)
cd /home/user/CPI-Web-Scarping/scripts/oneoff/dnata
R=runs_13_20
xvfb-run -a python3 fz_full.py 20261113 20261120 $R/fz_res.json DEL RUH KHI CMB IST ALY AMM; echo FZ_DONE
xvfb-run -a python3 air_saudia.py 2026-11-13 2026-11-20 $R/air_saudia_res.json RUH; echo SV_DONE
xvfb-run -a python3 air_egyptair.py 20261113 20261120 $R/air_egyptair_res.json; echo MS_DONE
xvfb-run -a python3 air_rj.py 2026-11-13 2026-11-20 $R/air_rj_res.json AMM; echo RJ_DONE
xvfb-run -a python3 air_pia.py DXB ISB 2026-11-13 2026-11-20 $R/air_pia_res.json; echo PK_DONE
xvfb-run -a python3 air_ba.py 2026-11-13 2026-11-20 $R/air_ba_res.json; echo BA_DONE
