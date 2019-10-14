@echo off
echo creating trace%1.txt
call py -3 nyr10ttl.py log=logs\%1.txt rewind trace > logs\trace%1.txt
