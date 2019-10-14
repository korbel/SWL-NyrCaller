@echo off
echo creating debug%1.txt
call py -3 nyr10ttl.py log=logs\%1.txt rewind > logs\debug%1.txt
