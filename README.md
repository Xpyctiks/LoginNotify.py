# loginNotify.py
This is a new version of my old bash script written in python, which sends all successfull SSH log-ins to your server via Telegram bot.  
Allows to monitor all connections to server and where are they made from.  
Also it is using local MySQL DB for whitelist IPs database.Using this DB allow to to use "IP + comment" from DB in the login message - usefull to understand who is connecting.  
If there is a connection from unknown IP (it doesn't exist in DB) - the login message has another view, and consists whois info about country and provider of that IP.  


Requires additionally two python packages:  
- mysql-connector-python  
- ipwhois  


For current moment I can't install those packages properly to Debian12 OS, so I did:  
pip3 install mysql-connector-python --break-system-packages  
pip3 install ipwhois --break-system-packages  
then copied all installed from /usr/local/lib/python3.11/dist-packages to /usr/lib/python3.11/ and what solved my problems.  


Installation:  
- Just download the script to any folder. For example, on Debian-based OS it could be /usr/local/bin/ folder.  
- Launch the script from CLI for the first time. It will generate a default configuration file.  
- Modify the config. file:  
    (You don't need to use already configured DB and user/pass if you want to do autosetup using mysql root password)  
    (But if you already have created DB and user/pass - just fill in the config file)  
    <dbName> - The name of DB you want to create  
    <dbUser> - user of the new DB  
    <dbPass> - password you want to set for new DB  
    <connectVia> - MySQL connect method - type "port" for connect via TCP(default) or "socket" to connect via socket.  
    <socket> - path to unix-socket of MySQL daemon. If you are using connection via socket.  
    <telegramToken> and <telegramChat> - for send login/logout messages to Telegram messenger.  
- Auto configuration of DB:  
    Launch script with parameter "initDB" and then mysql root password - all settings should be done automatically.Values of DB/User/Pass will be taken from config. file.  
- Finally, add to the end of /etc/pam.d/sshd next string: "session optional pam_exec.so [<path_to_this_script>/<this_script_name>]"  


Adding an IP address:  
- You can add new IP address with a comment using any mysql clients, cli, etc. Or use internal function of this script:  
  ./<this_script_name> addIP <IP> <Comment>  
  <IP> - an IP address to be added  
  <Comment> - comment for IP. Should be not large.  


Delete an IP address:  
- You can delete already existing IP address with a comment using any mysql clients, cli, etc. Or use internal function of this script:  
  ./<this_script_name> delIP <IP>  
  <IP> - an IP address to be deleted  
