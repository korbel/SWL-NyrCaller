@echo off
call py -3 nyr10ttl.py log=logs\%1.txt rewind trace > out%1.txt
