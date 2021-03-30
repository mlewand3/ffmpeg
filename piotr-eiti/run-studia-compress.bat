:: We cannot use NUC (Universal Naming Convention) with standard cmd/powershell
:: See more:
:: https://superuser.com/questions/282963/browse-an-unc-path-using-windows-cmd-without-mapping-it-to-a-network-drive

pushd "\\172.16.0.110\AVICON wymiana\DLA PIOTRKA\Studia"

python studia-compress.py

pause
