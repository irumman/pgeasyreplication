#Version 1.0

#!/usr/bin/python -tt

import os
import sys
import tarfile
import zipfile
import urllib
import commands
from optparse import OptionParser

pgdbuser = 'postgres'


pg_source_url=''
pg_download_dir=''
pg_install_dir=''
pg_config_option= ''

pgdata_master=''
master_ipaddress=''
master_pgport=''

pgdata_slave=''
slave_ipaddress=''
slave_pgport=''

pg_replication_user=''
sync_base_backup_file=''
recovery_conf_file=''
wal_level='hot_standby'
max_wal_senders = 5
wal_keep_segments = 32
hot_standby = 'on'


pgpool_host_address=''
pgpool_url=''
pgpool_download_dir=''
pgpool_install_dir=''
pgpool_config_option= ''


debug_mode=False

def log_output(outstr):
  if debug_mode:
    print 'DEBUG: ' + outstr
  return



  
def extract_file(path, to_directory='.'):
    if path.endswith('.zip'):
        opener, mode = zipfile.ZipFile, 'r'
    elif path.endswith('.tar.gz') or path.endswith('.tgz'):
        opener, mode = tarfile.open, 'r:gz'
    elif path.endswith('.tar.bz2') or path.endswith('.tbz'):
        opener, mode = tarfile.open, 'r:bz2'
    else: 
        raise ValueError, "Could not extract `%s` as no appropriate extractor is found" % path
    
    cwd = os.getcwd()
    print cwd
    os.chdir(to_directory)
    
    try:
        file = opener(path, mode)
        try: file.extractall()
        finally: file.close()
    finally:
        os.chdir(cwd)

def download_and_extract_source(src_url,download_dir):
  cmd = 'mkdir -p ' + download_dir
  log_output(cmd) 
  os.system(cmd)
  
  os.chdir(download_dir) 
  log_output(cmd)
  os.system(cmd)
  
  print 'Downloading files ...'
  cmd = 'wget ' + src_url
  log_output(cmd)
  #os.system(cmd)      
  txt = commands.getoutput(cmd) 
  log_output ('-----------------------')
  log_output(txt)
  log_output ('-----------------------')
  
  
  log_output('Finding downloaded file name')
  if src_url.find('f=') > 0: # for pgpool
    downloaded_file = src_url[src_url.rindex('=')+1:]
  else:  
    downloaded_file = src_url[src_url.rindex('/')+1:]
  log_output('Downloaded file = ' + downloaded_file) 
  
  os.chdir(download_dir)
  log_output('Extract downloaded file')
  cmd  = 'tar -zxf ' + downloaded_file
  os.system(cmd)
  #extract_file(downloaded_file)
  
  return downloaded_file

def download_postgres_from_src_install(src_url,download_dir,install_dir,config_option):
  
  log_output('Downloading Postgresql ...')
  downloaded_file = download_and_extract_source(src_url,download_dir)
  
  log_output('Install  Postgresql')
  dir=os.path.splitext(os.path.splitext(os.path.basename(downloaded_file))[0])[0]
  os.chdir(dir)
  cmd = './configure --prefix='+ install_dir + ' ' + config_option + ' && make && make install '
  os.system(cmd)
  
  cmd = 'useradd postgres'
  os.system(cmd)
  cmd = 'chown -R postgres.postgres ' + install_dir
  os.system(cmd)
  
  log_output('Set environment variables for PGENGINE')
  cmd = "su -l postgres -c \"echo '###Added by pgEasyReplication### ' >> .bash_profile \" "
  log_output(cmd)
  os.system(cmd)
  
  cmd = "su -l postgres -c \"echo 'export PATH=" + install_dir + ":\"\$PATH\" ' >> .bash_profile \" "
  log_output(cmd)
  os.system(cmd)
  
def initdb(pgengine,pgdata,conf_file_name,port,pg_replication_user):
  
  log_output('Initialize Postgresql')
  os.chdir(pgengine)
  cmd = 'su -l postgres -c "' + pgengine + '/' + 'initdb -D ' +  pgdata + '"'    
  log_output(cmd)
  os.system(cmd)
  
  log_output('Set environment variables')
  cmd = "su -l postgres -c \"echo '###Added by pgEasyReplication### ' >> .bash_profile \" "
  log_output(cmd)
  os.system(cmd)
  
  cmd = "su -l postgres -c \"echo 'export PGDATA=" + pgdata + " ' >> .bash_profile \" "
  log_output(cmd)
  os.system(cmd)
  
  
  cmd = "listen_addresses = '*'"
  cmd = cmd + '\nport = ' + port
  cmd = cmd + '\nlogging_collector = on '
  cmd = cmd + "\nlog_filename = 'postgresql-%a.log'"
  log_output(cmd)
  create_pgconf_file(pgdata,conf_file_name,cmd)
  
  
  log_output('Start postgresql ')
  cmd = 'su -l postgres -c "pg_ctl start -w -D ' + pgdata + ' " ' 
  log_output(cmd)
  os.system(cmd)


def create_pgconf_file(pgdata,conf_file_name,txt):
  conf_file = pgdata + '/' + conf_file_name
  postgresql_conf_file = pgdata + '/postgresql.conf'
  #f = open(conf_file,'wb+')
  #f.write(txt)
  #f.close()
  
  cmd = ' echo "' +  txt + '" >> ' + conf_file
  log_output(cmd)
  os.system(cmd)
    
  cmd  = 'chown postgres.postgres ' + conf_file
  log_output(cmd)
  os.system(cmd)
    
  cmd = "include '" + conf_file_name + "'"
  if not (cmd in open(postgresql_conf_file).read()):
    
    cmd = 'su -l postgres -c "echo \\\"include \'' + conf_file_name + '\' \\\"  >> ' + postgresql_conf_file + ' "'
    log_output(cmd)
    os.system(cmd)
  
  
  
def set_pgcluster_for_replication(pgengine,pgdata,conf_file_name,port,pg_replication_user, replica_host):
  
  
  cmd = 'wal_level = ' + wal_level
  cmd = cmd + '\nmax_wal_senders = ' + max_wal_senders
  cmd = cmd + '\nwal_keep_segments = ' + wal_keep_segments
  cmd = cmd + '\nhot_standby = ' + hot_standby
  log_output(cmd)
  create_pgconf_file(pgdata,conf_file_name,cmd)
  
  pghba_conf_file = pgdata + '/pg_hba.conf'
  cmd= 'host    replication ' + pg_replication_user +  '    '+ replica_host + '/0    trust'
  log_output(cmd)
  cmd = 'su -l postgres -c "echo \\\"' + cmd + '\\\"  >> ' + pghba_conf_file+ ' "'
  log_output(cmd)
  os.system(cmd)
  
  #cmd= 'host    all   all        0.0.0.0/0 md5'
  #log_output(cmd)
  #cmd = 'su -l postgres -c "echo \\\"' + cmd + '\\\"  >> ' + pghba_conf_file+ ' "'
  #log_output(cmd)
  #os.system(cmd)
  
  
  log_output('ReStart postgresql ')
  cmd = 'su -l postgres -c "pg_ctl restart -mf -w -D ' + pgdata + ' " ' 
  log_output(cmd)
  os.system(cmd)
  
  if pg_replication_user != 'all':
   log_output('Create replicator user ')
   cmd = 'psql -p ' + port + ' -c \\\"create user ' + pg_replication_user  + ' REPLICATION LOGIN ENCRYPTED PASSWORD \'' +  pg_replication_user + '\' \\\"'
   log_output(cmd)
   cmd = 'su -l postgres  ' + ' -c "' + cmd + '"'
   log_output(cmd)
   os.system(cmd)
  

def create_recovery_conf_file(master_host_address,master_pgport,replicator_user, recovery_conf_file):
  st = "standby_mode = 'on' # enables stand-by (readonly) mode "
  st = st + "\nprimary_conninfo = 'host= " + master_host_address + " port= " + master_pgport  + " user= " + replicator_user + "' "
  st = st + "\ntrigger_file = '/tmp/pg_failover_trigger'"
  log_output(st)
  cmd = 'echo "' + st + ' " > '  + recovery_conf_file
  log_output(cmd)
  os.system(cmd)
  
  cmd = 'chown postgres.postgres ' + recovery_conf_file
  log_output(cmd)
  os.system(cmd)


def create_copybasebackup(slave_host,slave_host_pgengine, slave_pgdata, master_pgengine, master_host, master_pgport, master_pguser, master_pgdata, recovery_conf_file, output_file):
  #Must run at master
  cmd = '#! /bin/sh'
  cmd = cmd + "\nssh -t " + slave_host + "  '" + slave_host_pgengine + "/pg_ctl stop -D " + slave_pgdata + "  '" 
  cmd = cmd + '\n' + master_pgengine + '/psql -h localhost  -p ' + master_pgport + ' -U ' + master_pguser + ' -c "select pg_start_backup(\'replication_backup\')"  '          
  cmd = cmd + '\nrsync -az ' + master_pgdata + '/*  ' + slave_host + ':'  +   slave_pgdata + '/ --exclude="postmaster.pid" --exclude="*.conf*"  '
  cmd = cmd + '\n' + master_pgengine + '/psql -h localhost -p ' + master_pgport + ' -U ' + master_pguser + ' -c "select pg_stop_backup()"  '          
  cmd = cmd + '\n scp ' + recovery_conf_file + '  ' + slave_host + ':' + slave_pgdata
  cmd = cmd + "\nssh -t " + slave_host + "  '" + slave_host_pgengine + "/pg_ctl start -w -D " + slave_pgdata + "  '" 
  log_output(cmd)
  
  
  f = open(output_file,'wb')
  f.write(cmd)
  f.close()
  
  cmd = 'chown postgres.postgres ' + output_file
  log_output(cmd)
  os.system(cmd)

def sync_slave_from_master(slave_host,slave_host_pgengine, slave_pgdata, master_pgengine, master_host, master_pgport, master_pguser, master_pgdata, recovery_conf_file, output_file):
  
  create_recovery_conf_file(master_ipaddress,master_pgport,pg_replication_user, recovery_conf_file)
  create_copybasebackup(slave_ipaddress,pgengine, pgdata_slave, pgengine, master_ipaddress, master_pgport, 'postgres', pgdata_master,recovery_conf_file,sync_base_backup_file)
  
  


def download_and_install_pgpool(src_url,download_dir,install_dir,config_option):
  log_output('Downloading Pgpool II ...')
  downloaded_file = download_and_extract_source(src_url,download_dir)
  log_output('Downloaded and extracted Pgpool successfully')
  
  log_output('Install  Pgpool II')
  dir=os.path.splitext(os.path.splitext(os.path.basename(downloaded_file))[0])[0]
  os.chdir(dir)
  cmd = './configure --prefix='+ install_dir + ' ' + config_option + ' && make && make install '
  os.system(cmd)
  log_output('Pgpool II installed successfully')
  
  cmd='chown -R postgres.postgres ' + install_dir
  log_output(cmd)
  os.system(cmd)
  
  cmd = 'useradd postgres'
  os.system(cmd)
  cmd = 'chown -R postgres.postgres ' + install_dir
  log_output(cmd)
  os.system(cmd)
  
  log_output('Set environment variables for PGPOOL ENGINE')
  cmd = "su -l postgres -c \"echo '###Added by pgEasyReplication for PGPOOL### ' >> .bash_profile \" "
  log_output(cmd)
  os.system(cmd)
  
  cmd = "su -l postgres -c \"echo 'export PATH=" + install_dir + ":\"\$PATH\" ' >> .bash_profile \" "
  log_output(cmd)
  os.system(cmd)
  
  #### Add /var/run/pgpool
  cmd = 'mkdir -p  /var/run/pgpool'
  log_output(cmd)
  os.system(cmd)
  
  cmd = 'chown -R postgres.postgres  /var/run/pgpool'
  log_output(cmd)
  os.system(cmd)  
  
  cmd = 'mkdir -p ' + install_dir + '/log'
  log_output(cmd)
  os.system(cmd)
  
  cmd = 'chown -R postgres.postgres ' + install_dir + '/log'
  log_output(cmd)
  os.system(cmd)   
  
  #Copy init.d script 
  dir= download_dir + '/' + os.path.splitext(os.path.splitext(os.path.basename(downloaded_file))[0])[0]
  cmd = 'cp ' + dir + '/redhat/pgpool.init /etc/init.d/pgpool'
  log_output(cmd)
  os.system(cmd)    

def configure_pghba_for_pgpool(pgcluster_host_address, pgcluster_port,pgengine, pgdata, dbuser,pgpool_host_address):
  
  pghba_conf_file = pgdata + '/pg_hba.conf'
  cmd= '##Added by pgEasyReplication for Pgpool##\nhost    all ' + dbuser +  '    '+ pgpool_host_address + '/0    trust'
  log_output(cmd)
  cmd = 'ssh -t ' +  pgcluster_host_address + " 'echo \\\"" + cmd + " \\\"  >> " + pghba_conf_file+ ";" + pgengine + "/pg_ctl reload -D " + pgdata + "'"
  log_output(cmd)
  cmd = 'su -l postgres -c "' +  cmd + '"'
  log_output(cmd)
  os.system(cmd)


def configure_pgpool_conf(pgpool_conf_file,master_host_address, master_pgport, master_pgdata, slave_host_address, slave_pgport, slave_pgdata, pgpool_home):
  
	# Commented out soem parameteres
  cmd = 'sed -i s/listen_addresses/#listen_addresses/g ' + pgpool_conf_file
  log_output(cmd)
  os.system(cmd)
  
  cmd = 'sed -i s/health_check_period/#health_check_period/g ' + pgpool_conf_file
  log_output(cmd)
  os.system(cmd) 
  
  
  cmd = 'sed -i s/health_check_user/#health_check_user/g ' + pgpool_conf_file
  log_output(cmd)
  os.system(cmd)  

  
  cmd = 'sed -i s/master_slave_mode/#master_slave_mode/g ' + pgpool_conf_file
  log_output(cmd)
  os.system(cmd)  
  
  cmd = 'sed -i s/master_slave_sub_mode/#master_slave_sub_mode/g ' + pgpool_conf_file
  log_output(cmd)
  os.system(cmd) 
  
  cmd = 'sed -i s/failover_command/#failover_command/g ' + pgpool_conf_file
  log_output(cmd)
  os.system(cmd) 
  
  cmd = 'sed -i s/backend_hostname0/#backend_hostname0/g ' + pgpool_conf_file
  log_output(cmd)
  os.system(cmd) 
  
  cmd = 'sed -i s/backend_port0/#backend_port0/g ' + pgpool_conf_file
  log_output(cmd)
  os.system(cmd) 
  
  cmd = 'sed -i s/backend_weight0/#backend_weight0/g ' + pgpool_conf_file
  log_output(cmd)
  os.system(cmd) 
  
  cmd = 'sed -i s/backend_data_directory0/#backend_data_directory0/g ' + pgpool_conf_file
  log_output(cmd)
  os.system(cmd) 
  
  cmd = 'sed -i s/backend_hostname1/#backend_hostname1/g ' + pgpool_conf_file
  log_output(cmd)
  os.system(cmd) 
  
  cmd = 'sed -i s/backend_port1/#backend_port1/g ' + pgpool_conf_file
  log_output(cmd)
  os.system(cmd) 
  
  cmd = 'sed -i s/backend_weight1/#backend_weight1/g ' + pgpool_conf_file
  log_output(cmd)
  os.system(cmd) 
  
  cmd = 'sed -i s/backend_data_directory1/#backend_data_directory1/g ' + pgpool_conf_file
  log_output(cmd)
  os.system(cmd) 
  
  cmd = 'sed -i s/sr_check_user/#sr_check_user/g ' + pgpool_conf_file
  log_output(cmd)
  os.system(cmd) 
  
  cmd = 'sed -i s/sr_check_period/#sr_check_period/g ' + pgpool_conf_file
  log_output(cmd)
  os.system(cmd) 
  
  cmd = 'sed -i s/debug_level/#debug_level/g ' + pgpool_conf_file
  log_output(cmd)
  os.system(cmd) 

  
  #Add parameters  
  
  f = open(pgpool_conf_file,'a')
  txt = '\n\n##Added by pgEasyReplication ###\n'
  f.write(txt)
  
  txt = 'listen_addresses =\'*\'\n'
  f.write(txt)
  
  txt = 'health_check_period =5\n'
  f.write(txt)
  
  txt = 'health_check_user =\'postgres\'\n'
  f.write(txt)
  
  txt = "backend_hostname0 ='" +  master_host_address  + "'\n"
  f.write(txt)
  
  txt = "backend_port0 =" +  master_pgport + "\n"
  f.write(txt)
  
  txt = "backend_weight0 = 1\n"
  f.write(txt) 
  
  txt = "backend_data_directory0 = '" + master_pgdata + "'\n"
  f.write(txt) 
  
  
  txt = "backend_hostname1 ='" +  slave_host_address  + "'\n"
  f.write(txt)
  
  txt = "backend_port1 =" +  slave_pgport + "\n"
  f.write(txt)
  
  txt = "backend_weight1 = 1\n "
  f.write(txt) 
  
  txt = "backend_data_directory1 = '" + slave_pgdata + "'\n"
  f.write(txt) 
  
  txt = "failover_command = 'sh  " + pgpool_home +  "/etc/failover.sh'\n"
  f.write(txt) 

  txt = "master_slave_mode = on\n"
  f.write(txt) 
 
  txt = "master_slave_sub_mode = 'stream'\n"
  f.write(txt) 
  
  txt = "sr_check_user = 'postgres'\n"
  f.write(txt) 
  
  txt = "debug_level  = 3\n"
  f.write(txt)
  
   
  f.close()
  

def create_and_copy_failover_script(failover_script_path,slave_host_address):
  txt = "#!/bin/sh\n "
  txt = txt + "# Execute command by failover.\n"
  txt = txt + "failed_node_id=$1\n"
  txt = txt + "failed_host_name=$2\n"
  txt = txt + "failed_port=$3\n"
  txt = txt + "failed_db_cluster=$4\n"
  txt = txt + "new_master_id=$5\n"
  txt = txt + "old_master_id=$6\n"
  txt = txt + "new_master_host_name=$7\n"
  txt = txt + "old_primary_node_id=$8\n"
  txt = txt + "trigger='/tmp/pg_failover_trigger'\n"
  txt = txt + "if [ $failed_node_id = $old_primary_node_id ];then      # master failed\n"
  txt = txt + "    ssh -t " + slave_host_address + "  'touch $trigger'      # let standby take over \n"
  txt = txt + "fi\n"

  f = open(failover_script_path,'wb')
  f.write(txt)
  f.close()
  
  
def read_parameter_file(parameter_file_path):

  f = open(parameter_file_path,'rU')
  for line in f:
    if line.count('pg_source_url') > 0:
      global pg_source_url
      pg_source_url = extract_parameter_value(line)
      log_output('pg_source_url = ' + pg_source_url)
      
    elif  line.count('pg_download_dir') > 0:
      global pg_download_dir
      pg_download_dir = extract_parameter_value(line)
      log_output('pg_download_dir = ' + pg_download_dir)
      
    elif  line.count('pg_install_dir') > 0:
      global pg_install_dir
      pg_install_dir = extract_parameter_value(line)  
      log_output('pg_install_dir = ' + pg_install_dir)
    
    elif  line.count('pg_config_option') > 0:
      global pg_config_option
      pg_config_option = extract_parameter_value(line)  
      log_output('pg_config_option = ' + pg_install_dir)

    #Master PgCluster Specific
    elif  line.count('pgdata_master') > 0:
      global pgdata_master
      pgdata_master = extract_parameter_value(line)   
      log_output('pgdata_master = ' + pgdata_master) 
     
      
    elif  line.count('master_ipaddress') > 0:
      global master_ipaddress
      master_ipaddress = extract_parameter_value(line)     
      log_output('master_ipaddress = ' + master_ipaddress) 
     
    elif  line.count('master_pgport') > 0:
      global master_pgport
      master_pgport = extract_parameter_value(line)     
      log_output('master_pgport = ' + master_pgport) 

    
    #Slave PgCluster Specific
    elif  line.count('pgdata_slave') > 0:
      global pgdata_slave
      pgdata_slave = extract_parameter_value(line)   
      log_output('pgdata_slave = ' + pgdata_slave) 
     
      
    elif  line.count('slave_ipaddress') > 0:
      global slave_ipaddress
      slave_ipaddress = extract_parameter_value(line)     
      log_output('slave_ipaddress = ' + slave_ipaddress) 
     
    elif  line.count('slave_pgport') > 0:
      global slave_pgport
      slave_pgport = extract_parameter_value(line)     
      log_output('slave_pgport = ' + slave_pgport)  
    
    
    #Pg Srreaming Replication Specific 
    elif  line.count('pg_replication_user') > 0:
      global pg_replication_user
      pg_replication_user = extract_parameter_value(line)   
      log_output('pg_replication_user = ' + pg_replication_user) 
     
    elif  line.count('sync_base_backup_file') > 0:
      global sync_base_backup_file
      sync_base_backup_file = extract_parameter_value(line)      
      log_output('sync_base_backup_file = ' + sync_base_backup_file) 
      
    elif  line.count('recovery_conf_file') > 0:
      global recovery_conf_file
      recovery_conf_file = extract_parameter_value(line)     
      log_output('recovery_conf_file = ' + recovery_conf_file) 
    
    elif  line.count('wal_level') > 0:
      global wal_level
      wal_level = extract_parameter_value(line)     
      log_output('wal_level = ' + wal_level) 
    
    elif  line.count('max_wal_senders') > 0:
      global max_wal_senders
      max_wal_senders = extract_parameter_value(line)     
      log_output('max_wal_senders = ' + max_wal_senders)   
    
    elif  line.count('wal_keep_segments') > 0:
      global wal_keep_segments
      wal_keep_segments = extract_parameter_value(line)     
      log_output('wal_keep_segments = ' + wal_keep_segments)     
    
    elif  line.count('hot_standby') > 0:
      global hot_standby
      hot_standby = extract_parameter_value(line)     
      log_output('hot_standby = ' + hot_standby)       
    
    
    #Pgpool Download and Install Specific
    
    elif  line.count('pgpool_host_address') > 0:
      global pgpool_host_address
      pgpool_host_address = extract_parameter_value(line)   
      log_output('pgpool_url = ' + pgpool_host_address) 
      
    elif  line.count('pgpool_url') > 0:
      global pgpool_url
      pgpool_url = extract_parameter_value(line)   
      log_output('pgpool_url = ' + pgpool_url) 
     
    elif  line.count('pgpool_download_dir') > 0:
      global pgpool_download_dir
      pgpool_download_dir = extract_parameter_value(line)      
      log_output('pgpool_download_dir = ' + pgpool_download_dir) 
      
    elif  line.count('pgpool_install_dir') > 0:
      global pgpool_install_dir
      pgpool_install_dir = extract_parameter_value(line)     
      log_output('pgpool_install_dir = ' + pgpool_install_dir) 
     
    elif  line.count('pgpool_config_option') > 0:
      global pgpool_config_option
      pgpool_config_option = extract_parameter_value(line)     
      log_output('pgpool_config_option = ' + pgpool_config_option) 


def create_pgpool_startup_script(init_file,pgpool_home):
 
  
  cmd = 'PGPOOL_HOME=' + pgpool_home.replace('/','\/') + "\\n"
  cmd = cmd + 'PGPOOLENGINE=\$PGPOOL_HOME\/bin\\n'
  cmd = cmd + 'PGPOOLDAEMON=\$PGPOOLENGINE\/pgpool\\n'
  cmd = cmd + 'PGPOOLCONF=\$PGPOOL_HOME\/etc\/pgpool.conf\\n'
  cmd = cmd + 'PGPOOLPIDDIR=\/var\/run\/pgpool\\n'
  cmd = cmd + 'PGPOOLLOG=\$PGPOOL_HOME\/log\/pgpool.log\\n'
  cmd = cmd + 'test -x \$PGPOOLDAEMON || exit 5\\n\\n'
  cmd = 'sed -i s/"test -x \$PGPOOLDAEMON || exit 5"/"' + cmd + '"/g ' + init_file
  
  log_output(cmd) 
  os.system(cmd)
  
  
  cmd = 'sed -i s/"killproc \/usr\/bin\/pgpool"/"#killproc \/usr\/bin\/pgpool\\n\$PGPOOLDAEMON stop \& >> "\$PGPOOLLOG" 2>\&1 < \/dev\/null"/g ' + init_file
  #cmd = 'sed -i s/"killproc \/usr\/bin\/pgpool"/"#killproc \/usr\/bin\/pgpool\\n\$PGPOOLDAEMON stop \& "/g ' + init_file

  log_output(cmd) 
  os.system(cmd)              
  
  
def extract_parameter_value(prm_val):
   prm_val = prm_val[prm_val.index('=')+1:]
   prm_val = prm_val.replace("'","")
   prm_val = prm_val.strip()   
   return prm_val        
  
def main():
  
  parser = OptionParser(usage="usage: %prog [options] ")
  parser.add_option("-f",action="store", dest="parameter_file_path", help="Read configuration file")
  parser.add_option("--download-install-postgres",action="store_true", dest="download_install_postgres", help="Download Postgresql Source and Install")
  parser.add_option("--init-master-pgcluster",action="store_true", dest="init_master", help="Prepare Pgcluster as Master")
  parser.add_option("--init-slave-pgcluster",action="store_true", dest="init_slave", help="Prepare Pgcluster for Slave")
  parser.add_option("--config-master-for-repl",action="store_true", dest="conf_master_for_repl", help="Configure master pgcluster for replication")
  parser.add_option("--config-slave-for-repl",action="store_true", dest="conf_slave_for_repl", help="Configure slave pgcluster for replication")
  parser.add_option("--sync-slave-with-master",action="store_true", dest="sync_slave", help="Sync Slave with Master for Replication; Execute this from Master")
  parser.add_option("--download-install-pgpool",action="store_true", dest="download_install_pgpool", help="Download Pgpool II Source and Install")
  parser.add_option("--setup-pgpool-env",action="store_true", dest="setup_pgpool_env", help="Setup Pgpool II environment for Streaming Replication with given Master/Slave")
  parser.add_option("-d", "--debug",action="store_true", dest="debug_mode", help="Run in debug mode")
  (options, args) = parser.parse_args()
  
  global debug_mode
  debug_mode = options.debug_mode
  
  parameter_file_path = options.parameter_file_path
  if not parameter_file_path:
    print "!!!Please provide configuration file path!!!"
    parser.print_help()
    return
  
  read_parameter_file(parameter_file_path)  
  
  if options.download_install_postgres:
   download_postgres_from_src_install(pg_source_url,pg_download_dir,pg_install_dir,pg_config_option)
  
  pgengine = pg_install_dir + '/bin'
  conf_file_name = 'pgeasyreplication.postgresql.conf'
  
  if options.init_master:
    print "Preparing master pgcluster ..."
    #Prepare master
    initdb(pgengine,pgdata_master,conf_file_name,master_pgport,pg_replication_user)
    print "Master Pgcluster prepared at " + pgengine  
     
  if options.init_slave:
    print "Preparing master pgcluster ..."
    #Prepare Slave
    initdb(pgengine,pgdata_slave,conf_file_name,slave_pgport,pg_replication_user)
    print "Slave Pgcluster prepared at " + pgengine  
    
  if options.conf_master_for_repl:
    set_pgcluster_for_replication(pgengine,pgdata_master,conf_file_name,master_pgport,pg_replication_user, slave_ipaddress)
  
  if options.conf_slave_for_repl:
    set_pgcluster_for_replication(pgengine,pgdata_slave,conf_file_name,slave_pgport,pg_replication_user, master_ipaddress)    
    
  if options.sync_slave:
    
    create_recovery_conf_file(master_ipaddress,master_pgport,pg_replication_user, recovery_conf_file)
    create_copybasebackup(slave_ipaddress,pgengine, pgdata_slave, pgengine, master_ipaddress, master_pgport, pgdbuser, pgdata_master,recovery_conf_file,sync_base_backup_file)
    cmd = 'su -l postgres -c "sh ' + sync_base_backup_file + ' " '
    log_output(cmd)
    os.system(cmd)
       
  if options.download_install_pgpool:
    download_and_install_pgpool(pgpool_url,pgpool_download_dir,pgpool_install_dir,pgpool_config_option)
  
  
  if options.setup_pgpool_env: 
	  #Master pgcluster pg_hba conf for Pgpool
    configure_pghba_for_pgpool(master_ipaddress, master_pgport,pgengine,pgdata_master, pgdbuser,pgpool_host_address)
    configure_pghba_for_pgpool(slave_ipaddress, slave_pgport,pgengine,pgdata_slave, pgdbuser,pgpool_host_address)
    pgpool_conf_file= pgpool_install_dir + '/etc/pgpool.conf'
    cmd = 'cp ' + pgpool_install_dir + '/etc/pgpool.conf.sample  ' +   pgpool_conf_file
    log_output(cmd)
    os.system(cmd)
    pcp_conf_file= pgpool_install_dir + '/etc/pcp.conf'
    cmd = 'cp ' + pgpool_install_dir + '/etc/pcp.conf.sample  ' +   pcp_conf_file
    log_output(cmd)
    os.system(cmd)
    configure_pgpool_conf(pgpool_conf_file,master_ipaddress, master_pgport, pgdata_master, slave_ipaddress, slave_pgport, pgdata_slave, pgpool_install_dir)
    failover_script_path = pgpool_install_dir + '/etc/failover.sh'
    create_and_copy_failover_script(failover_script_path,slave_ipaddress)  
    pgpool_init_file = '/etc/init.d/pgpool' 
    create_pgpool_startup_script(pgpool_init_file,pgpool_install_dir)
    
  return
  
  
if __name__ == '__main__':
 main()
