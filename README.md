## About

**Gofed** is a set of tools that automates the packaging process of golang development source codes.

Supported features:
* a spec file generator for the github.com, code.google.com, and bitbucket.org repositories
* preparation of the Fedora's Review Request for a new golang package
* golang imports discovering (dependency on other imports or packages)
* comparison of APIs (exported symbols) of two golang projects
* scan of available golang packages, construction of dependency graphs of packages
* other useful commands (parallel push, pull or update of all chosen branches, ...)

## Installation
The repository provides a spec file for Fedora. The package can be build as:

   ```vim
   $ wget https://github.com/ingvagabund/GolangPackageGenerator/archive/<commit>/gpg-<shortcommit>.tar.gz
   $ cp gpg-<shortcommit>.tar.gz /home/<user>/rpmbuild/SOURCES/.
   $ rpmbuild -ba *.spec
   $ rpm -Uvh <built rpm>.rpm
   ```

## Launching
To generate a spec file for the github https://github.com/stretchr/respond repository, run the following command:

   ```vim
   $ gofed github2spec -p stretchr -r respond --commit fb9c7353c67cdeccb10af1320b978c5a1e401e9b -f
   ```

Output:
   ```vim
   Repo URL:
   https://github.com/stretchr/respond

   (1/4) Checking if the package already exists in PkgDB
   (2/4) Creating spec file
   (3/4) Downloading tarball
   (4/4) Discovering golang dependencies
   Class: github.com/stretchr/testify (golang-github-stretchr-testify) PkgDB=True

   Spec file golang-github-stretchr-respond.spec at:
   /tmp/test/golang-github-stretchr-respond/fedora/golang-github-stretchr-respond
   ```
   
At the beginning, golang checks the Fedora repository if the package already exists. If not, it creates a spec file (needs to be filled for missing data), downloads the tarball, and lists all dependencies (classes of imports decomposed by a repository - common import path prefix).

#### Dependency discovering
To discover imports and dependencies of packages in the https://github.com/rackspace/gophercloud repository, run the following command on the repository's tarball:

   ```vim
   $ gofed ggi -c -s -d
   ```

Output:

   ```vim
   Class: github.com/mitchellh/mapstructure (golang-github-mitchellh-mapstructure) PkgDB=True
   Class: github.com/racker/perigee (golang-github-racker-perigee) PkgDB=True
   Class: github.com/rackspace/gophercloud (golang-github-rackspace-gophercloud) PkgDB=True
   Class: github.com/tonnerre/golang-pretty (golang-github-tonnerre-golang-pretty) PkgDB=True
   ```

When running with the -d option, gofed checks if the dependency is already packaged in the PkgDB database.

#### Check of up2date dependencies in Fedora
To check if all dependencies of a package are up-to-date in Fedora (for example kubernetes), run the following command on the package's Godeps.json file:

   ```vim
   $ gofed check-deps Godeps.json
   ```

Output:

   ```vim
   package golang-github-davecgh-go-spew outdated
   package golang-github-onsi-gomega outdated
   package golang-github-onsi-ginkgo outdated
   package golang-github-ghodss-yaml outdated
   package golang-github-spf13-pflag outdated
   ```

When running with the -v option, gofed displays status of all dependencies.
When running with the -l option, gofed does not perform git|hg pull on each repository.

#### Check devel builds of all golang packages

To create a local database of exported symbols, provided import paths, and imported paths each development build, run:

   ```vim
   $ gofed scan-imports -c
   ```
   
   This command downloads every build providing source codes. Each build is parsed and exported symbols are extracted. Every golang project consists of a package. Every package in a project is defined by its path and by a set of symbols that developer can use. Once the scan is finished, all symbols are locally saved in XML files. These files can be further analyzed.
   Extracted information can be queried for used or provided import paths. The command also constructs a dependency graph for a given package.
   Implicitly, only outdated packages are scanned so once the database is created, there is no need to regenerate it for all packages every time.
   
#### Golang dependency graph

To display a dependency graph for a package, for example docker-io, run:

   ```vim
   $ gofed scan-deps -g -o docker.png docker-io
   ```

This command generates a PNG picture, in this case named docker.png, with the dependency graph.

![docker-io dependencies](https://raw.githubusercontent.com/ingvagabund/GolangPackageGenerator/master/docker.png)

#### Golang project decomposition

To display a decomposition of a project into a dependency graph, for example [prometheus](https://github.com/prometheus/prometheus), run the following command in project's directory:

   ```vim
   $ gofed scan-deps -d github.com/prometheus/prometheus --from-dir . --skip-errors -g -o prometheus.png
   ```

This command generates a PNG picture, in this case named prometheus.png, with the dependency graph.

![prometheus decomposition](https://raw.githubusercontent.com/ingvagabund/GolangPackageGenerator/master/prometheus.png)


#### API check

To see differences in exported symbols between two releases, commits, or versions of the same project, use the "gofed apidiff" command in the following format:

   ```vim
   $ gofed apidiff <DIR1> <DIR2>
   ```

For example, to check API of etcd between etcd-2.0.3 and etcd-2.0.4 versions (untared tarballs), run:

   ```vim
   $ gofed apidiff etcd-2.0.3 etcd-2.0.4
   ```
   
   Output
   
   ```vim
   Package: etcdserver
      -GetClusterFromPeers func removed
   Package: etcdserver/etcdhttp
      -function NewPeerHandler: parameter count changed: 2 -> 3
   ```
   
   To get new symbols and other information, use the -a option:
   
   ```vim
   Package: etcdserver
      struct Cluster has different number of fields
      struct Cluster: fields are reordered
      +struct Cluster: new field 'index'
      +GetClusterFromRemotePeers func added
      +UpdateIndex func added
      -GetClusterFromPeers func removed
   Package: etcdserver/etcdhttp
      -function NewPeerHandler: parameter count changed: 2 -> 3
   Package: pkg/wait
      +WaitTime type added
      +NewTimeList func added
      +Wait func added
   Package: wal
      +WALv2_0Proxy variable/constant added
   ```
   
   Lines starting with the minus symbol ("-") are breaking backward compatibility. Lines starting with the plus symbol ("+") are new. Other lines reports other issues.

#### gofed-web client

To use gofed-web service, use "gofed client" command. You can query regularly
updated database of APIdiffs to speed up APIdiff inspections.


To see all available projects with APIdiff trend sorted alphabetically, use:

   ```vim
   $ gofed client -l --FMT "full_name:trend" | sort
   ```

   Output:

   ```vim
    cadvisor                                              165
    docker-io                                             123
    etcd                                                  219
    fleet                                                   5
    golang-bitbucket-kardianos-osext                       18
    golang-bitbucket-ww-goautoneg                           0
    ...
   ```

To see last two commits in project cadvisor and their API affection, use:

   ```vim
   $ gofed client -p cadvisor -m -q 2 -J 
   ```

   ```vim
   [
     {
       "added": [],
       "author": "Vish Kannan <vishh@users.noreply.github.com>",
       "commit": "769738ba88e4568b47c1fe7fadfe9cb56cb4b19c",
       "commit_msg": "Merge pull request #884 from hacpai/fixbug-issue-88",
       "date": "2015-09-17 17:52:56+00:00",
       "modified": [
         {
           "change": "function New: parameter count changed: 4 -> 5",
           "package": "storage/elasticsearch"
         }
       ]
     },
     {
       "added": [],
       "author": "Vish Kannan <vishh@users.noreply.github.com>",
       "commit": "7327cfe267570e73e0f419e66a97b1f0811d0034",
       "commit_msg": "Merge pull request #885 from rjnagal/docke",
       "date": "2015-09-15 18:49:53+00:00",
       "modified": []
     }
   ]
   ```
See "gofed client --help" for more info and available commands.

