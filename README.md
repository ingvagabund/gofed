## About

**Gofed** is a set of tools with a goal to automate packaging of golang devel source codes.

What it basically supports:
* spec file generator for github.com, code.google.com and bitbucket.org repositories
* preparation of Fedora's Review Request for a new golang package
* golang imports discovering (dependency on other imports/packages)
* comparision of APIs (exported symbols) of two golang projects
* scan of available golang packages, construction of dependency graphs of packages
* other useful commands (parallel push, pull or update of all chosen branches, ...)

## Instalation
The repo provides a spec file for Fedora. The package can be build as:

   ```vim
   $ wget https://github.com/ingvagabund/GolangPackageGenerator/archive/<commit>/gpg-<shortcommit>.tar.gz
   $ cp gpg-<shortcommit>.tar.gz /home/<user>/rpmbuild/SOURCES/.
   $ rpmbuild -ba *.spec
   $ rpm -Uvh <built rpm>.rpm
   ```

## Launch it
To generate spec file for github repository https://github.com/stretchr/respond:

   ```vim
   $ gofed github2spec stretchr respond fb9c7353c67cdeccb10af1320b978c5a1e401e9b
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
   
First it checks fedora repo if the package already exists. If not, it creates a spec file (needs to be filled for missing data), downloads the tarball and lists all dependencies (classes of imports decomposed by a repository (common import path prefix).

#### Dependency discovering
To discover imports and dependecies on packages for https://github.com/rackspace/gophercloud, run the following command on its tarball:

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

Running with -d option, the gofed checks if the dependency is already packaged in PkgDB.

#### Check of up2date dependencides in Fedora
To check if all dependecies of a package are at least up2date in Fedora (e.g. kubernetes), run the following command on its Godeps.json file:

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

Running with -v option display status of all dependencies.
Running with -l option will not run git|hg pull on each repository.

#### Check devel builds of all golang packages

In order to create a local database of exported symbols, provided import paths and imported paths for each devel build, you can run:

   ```vim
   $ gofed scan-imports -c
   ```
   
   This will download every build providing source codes. Each build is parsed and exported symbols are extracted. Every golang project consists of package. Every package in a project is defined by its path and a set of symbols developer can use. Once the scan finished, all symbols are locally saved in xml files. These files can be further analyzed.
   Extracted information can be queried for used or provided import paths. It is also used for construction of a dependency graph for a given package.
   Implicitelly, only outdated packages are scaned so once you have the database, you don't have to regenerate it for all packages again.
   
#### Golang dependency graph

To display a dependency graph for a package, e.g. docker-io, run:

   ```vim
   $ gofed scandeps -g -o docker.png docker-io
   ```

This will generate a png picture docker.png with the graph.

![docker-io dependencies](https://raw.githubusercontent.com/ingvagabund/GolangPackageGenerator/master/docker.png)

#### API check

To see differences in exported symbols between two releases/commits/versions of the same project, use "gofed apidiff DIR1 DIR2" command. To check API of etcd between etcd-2.0.3 and etcd-2.0.4 (untared tarballs) run:

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
   
   To get new symbols and other information, use -a option:
   
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
   
   Lines starting with minus symbol "-" are breaking back-compatibility. Lines starting with plus ysmbol "+" are new. Other lines reports other issues.
