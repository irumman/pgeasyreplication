pgeasyreplication
=================

pgEasyReplication - is a tool to setup Postgresql cluster and setting up streaming replicaiton between master and slave.
Also it has the capability to install pgpool II and setup high availability in the database infrastructure.

python pgEasyReplication.py --help
Usage: pgEasyReplication.py [options] 

Options:
  -h, --help            show this help message and exit
  -f PARAMETER_FILE_PATH
                        Read configuration file
  --download-install-postgres
                        Download Postgresql Source and Install
  --init-master-pgcluster
                        Prepare Pgcluster as Master
  --init-slave-pgcluster
                        Prepare Pgcluster for Slave
  --config-master-for-repl
                        Configure master pgcluster for replication
  --config-slave-for-repl
                        Configure slave pgcluster for replication
  --sync-slave-with-master
                        Sync Slave with Master for Replication; Execute this
                        from Master
  --download-install-pgpool
                        Download Pgpool II Source and Install
  --setup-pgpool-env    Setup Pgpool II environment for Streaming Replication
                        with given Master/Slave
  -d, --debug           Run in debug mode

