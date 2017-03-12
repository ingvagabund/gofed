## About

**Gofed** is a tool set aimed at automation of packaging of golang projects and analysis of Go ecosystem.

**Per project support**:
* Spec file generator for the github.com, code.google.com, and bitbucket.org repositories
* Fedora's Review Request generator for new golang packages
* Comparison of APIs (exported symbols) of two golang projects
* Go source code analysis: dependency discovery (imported projects), tests and main package detection
* Dependency approximation: approximate Godeps.json for your project 

**Per distribution support**:
* Multicommands: run scratch-builds, builds, updates, etc. on multiple branches with one command
* Update your package with one command using a wizard
* Project snapshot checker: check current state of all dependencies of your project (up2date, outdated, missing)
* Spec file bumper: update you spec file just be specifying commit
* Create trackers for your Go projects in distribution
* Lint your spec file: detection of missing Provides, [Build]Requires

**Per ecosystem support**:
* Distribution analysis: dependency graph builders, new go project discovery


## Quick start

1. Clone the repository
2. Install python modules
3. Install packages
4. Set up gofed
5. Alias ./hach/gofed.sh
6. Run gofed

```sh
$ git clone https://github.com/gofed/gofed; cd gofed
$ sudo dnf install python-pip python-devel redhat-rpm-config
$ sudo pip install -r requirements.txt
$ sudo dnf install -y graphviz koji rpm-build rpmdevtools
$ ./hack/prep.sh
$ alias gofed=$(realpath ./hack/gofed.sh)
$ gofed
```

Or if you prefer a containerized solution, you can run:

```sh
$ sudo docker pull gofed/gofed:v1.0.1
$ sudo docker run -it gofed/gofed:v1.0.1 /bin/bash
```

### Experimental: run gofed command as a container

Currently supported commands:

* gofed repo2spec (and its equivalents)
* gofed inspect

**Example**:

```sh
./hack/gofed-docker.sh repo2spec --detect github.com/kr/text -f [--force]
```

In order to run gofed command as a container, one needs to add itself to the docker group:

```sh

$ sudo groupadd docker
$ sudo useradd -G docker USERNAME
$ newgrp docker
```


## Resource management

Some **gofed** commands require working with resources.
To provide a transparent interface, commands accept resource declarations only.
Processed resources (source code tarball, rpms, etc.) may be stored
under local directories dependening on the **gofed** system configuration.
Check out ``infra.conf`` under the ``third_party/gofed_infra/system/config`` directory.
By default, directories under ``/var/lib/gofed`` are expected.
When running ``./hack/prep.sh`` all resource working directories are set to point
to their equivalents under the ``working_directory`` directory.

Resources that have been processed are not cleaned automatically.
There are two ways to provide a cleaning mechanism:

* cleaning daemons
* one time command

### Cleaning daemons

Check out ``gofed-resources-client.service`` and ``gofed-resources-provider.service`` under
the ``third_party/gofed_infra/system/daemons`` directory.
The services are meant to be run as user services as ``systemctl --start start gofed-resources-[client|provider].service``.
Before running the services make sure both are installed under the ``/usr/lib/systemd/user`` directory.

Required service are generated by ``hack/prep.sh``.

Services cannot be run within containerized gofed.

### One time command

Optionally, the daemons can be replaced with the ``gofed clean-resources`` command.
The command cleans all resources retrived by gofed.
On the other hand, the command has to be run manually every time.

## Gofed land tour

Simple intro to the tools

### Spec file generator

One of the common use cases is to generate a spec file.
The fastest way to generate one for a Go project (e.g. https://github.com/cpuguy83/go-md2man) is to run:

   ```vim
   $ gofed repo2spec --detect https://github.com/cpuguy83/go-md2man --commit 2724a9c9051aa62e9cca11304e7dd518e9e41599 -f --with-build
   ```

The project is already packaged in Fedora. Thus, use the ``--force`` option too.

Output:
   ```vim
   Repo URL: github.com/cpuguy83/go-md2man
   Commit: 2724a9c9051aa62e9cca11304e7dd518e9e41599
   Name: golang-github-cpuguy83-go-md2man
   
   (1/4) Checking if the package already exists in PkgDB
   (2/4) Collecting data
   (3/4) Generating spec file
   (4/4) Discovering golang dependencies
   Discovering package dependencies
   	Class: github.com/russross/blackfriday (golang-github-russross-blackfriday) PkgDB=True
   
   Spec file golang-github-cpuguy83-go-md2man.spec at /tmp/test/golang-github-cpuguy83-go-md2man/fedora/golang-github-cpuguy83-go-md2man
   ```

At the beginning, golang checks the Fedora repository to see if the package already exists.
If not, it creates a spec file (needs to have missing data filled in),
retrieves tarball with source code,
and checks the current state of all dependencies (classes of imports decomposed by a repository - common import path prefix).

The ``gofed repo2spec`` command generates the spec file only.
To download project's tarball, change your working directory to
``/tmp/test/golang-github-cpuguy83-go-md2man/fedora/golang-github-cpuguy83-go-md2man``
and run ``gofed fetch --spec``:

   ```sh
   $ gofed fetch --spec
   Detecting spec file in the current directory...
   'golang-github-cpuguy83-go-md2man.spec' detected
   Parsing spec file
   ipprefix: github.com/cpuguy83/go-md2man
   commit: 2724a9c9051aa62e9cca11304e7dd518e9e41599
   Fetching https://github.com/cpuguy83/go-md2man/archive/2724a9c9051aa62e9cca11304e7dd518e9e41599/go-md2man-2724a9c.tar.gz ...
   ```

The spec file and tarball are ready for analysis.

### Dependency discovery

To discover imports and dependencies of the previous project, run the following command inside of the repository's tarball:

   ```vim
   $ tar -xf go-md2man-2724a9c.tar.gz
   $ cd go-md2man-2724a9c9051aa62e9cca11304e7dd518e9e41599
   $ gofed ggi -c -s -d -v
   ```

Output:

   ```vim
   Class: github.com/russross/blackfriday (golang-github-russross-blackfriday) PkgDB=True
   ```

When running with the -d option, gofed checks if the dependency is already packaged in the PkgDB database.
To show only dependencies that are not packaged in PkgDB, run the command without the ``-v`` option.

When running ``gofed ggi`` without any options, list of all dependencies of devel part as shown:

```vim
   $ gofed ggi
	github.com/russross/blackfriday
```

To show all dependencies, run the command with the ``--all-occurrences`` option:

```vim
$ gofed ggi --all-occurrences
	github.com/cpuguy83/go-md2man/md2man
	github.com/russross/blackfriday
```

### Check project dependencies in Fedora

To check if all dependencies of a package are up-to-date in Fedora (for example etcd), run the following command on the package's Godeps.json file:

   ```vim
   $ gofed check-deps --godeps Godeps.json
   ```

Output:

   ```vim
   github.com/spf13/cobra is newer in distribution
   github.com/kballard/go-shellquote is up-to-date
   github.com/matttproud/golang_protobuf_extensions is newer in distribution
   golang.org/x/crypto is newer in distribution
   golang.org/x/net is up-to-date
   github.com/codegangsta/cli is newer in distribution
   github.com/beorn7/perks is up-to-date
   github.com/russross/blackfriday is up-to-date
   github.com/coreos/go-systemd is newer in distribution
   bitbucket.org/ww/goautoneg is up-to-date
   github.com/shurcooL/sanitized_anchor_name is up-to-date
   github.com/olekukonko/tablewriter is up-to-date
   github.com/olekukonko/ts is up-to-date
   github.com/google/btree is up-to-date
   github.com/gogo/protobuf is up-to-date
   ...
   ```

By default, the rawhide distribution is checked.

To speed up the check, it is recommended to scan the distribution first (see below).

### Distribution analysis

#### Scan distribution for available projects

To scan the distribution for available Go projects, run the following command:

   ```vim
   $ gofed scan-distro -v
   ```

The command checks the distribution (Fedora rawhide by default) for all Go projects
packaged in the distribution with the generic name prefixed with ``golang-*``.
To provide a list of additional packages, use the ``--custom-packages`` option.
Then, the list of the latest builds for packages is retrieved.
Data from the builds are extracted and ready for analysis.

Data retrieved by ``gofed scan-distro`` is  usually prerequisite for other scans such as:

* ``gofed scan-packages``
* ``gofed scan-deps``

or checks:

* ``gofed check-deps``

IMPORTANT: in order to run the command, all rpms must be scanned succesfully.
If it does not hold, ``gofed scan-distro`` does not generate the distribution snapshot
which is needed by the commands listed above.
Thus, run the command with ``--skip-failed`` option to make sure the snapshot is generated.
    
#### Golang dependency graph

To display a dependency graph for a package, for example docker-io, run:

   ```vim
   $ gofed scan-deps -v -g -o docker.png docker
   ```

This command generates a PNG picture, in this case named docker.png, with the dependency graph.

![docker-io dependencies](https://raw.githubusercontent.com/gofed/gofed/master/docs/images/docker.png)

IMPORTANT: before displaying the generated picture, checkout its size. Huge images tend to freeze your computer.

#### Golang project decomposition

To display a decomposition of a project into a dependency graph, for example [prometheus](https://github.com/prometheus/prometheus), run the following command in project's directory:

   ```vim
   $ gofed scan-deps -v -d github.com/prometheus/prometheus --from-dir . -g -o prometheus.png
   ```

This command generates a PNG picture, in this case named prometheus.png, with the dependency graph.

![prometheus decomposition](https://raw.githubusercontent.com/gofed/gofed/master/docs/images/prometheus.png)


#### API check

To see differences in exported symbols between two releases, commits, or versions of the same project, use the "gofed apidiff" command in the following format:

   ```vim
   $ gofed apidiff --reference="upstream:project[:commit]" --compare-with="upstream:project[:commit]"
   ```

For example, to check API of etcd between etcd-2.3.3 and etcd-2.2.4, run:

   ```vim
   $ gofed apidiff --reference="upstream:github.com/coreos/etcd:c41345d393002e87ae9e7023234b1c1e04ba9626" --compare-with="upstream:github.com/coreos/etcd:bdee27b19e8601ffd7bd4f0481abe9bbae04bd09"
   ```
Commit ``c41345d393002e87ae9e7023234b1c1e04ba9626`` correponds to ``etcd-v2.3.3``, commit ``bdee27b19e8601ffd7bd4f0481abe9bbae04bd09`` to ``etcd-v2.2.4``.

   
   Output
   
   ```vim
   -etcdctlv3/command: function removed: NewDeleteRangeCommand
   -etcdctlv3/command: function removed: NewRangeCommand
   -etcdserver/api/v3rpc: function removed: New
   -etcdserver/api/v3rpc: function removed: handler.Compact
   -etcdserver/api/v3rpc: function removed: handler.DeleteRange
   -etcdserver/api/v3rpc: function removed: handler.Put
   -etcdserver/api/v3rpc: function removed: handler.Range
   -etcdserver/api/v3rpc: function removed: handler.Txn
   ...
   ```
   
   To get new symbols and other information, use the -a option:
   
   ```vim
   ...
   +etcdctlv3/command: new function: NewGetCommand
   +etcdctlv3/command: new function: simplePrinter.Get
   +etcdctlv3/command: new function: NewCompactionCommand
   +etcdctlv3/command: new function: simplePrinter.Watch
   ~etcdctlv3/command: function updated: -type differs: selector != pointer
   ~etcdctlv3/command: function updated: -type differs: selector != pointer
   -etcdctlv3/command: function removed: NewDeleteRangeCommand
   -etcdctlv3/command: function removed: NewRangeCommand
   +etcdctlv3/command: new variable: ExitIO
   +etcdctlv3/command: new variable: ExitInvalidInput
   +etcdctlv3/command: new variable: ExitBadArgs
   +etcdctlv3/command: new variable: ExitError
   +etcdctlv3/command: new variable: ExitBadConnection
   ...
   ```
   
Lines starting with the minus symbol ("-") break backward compatibility.
Lines starting with the plus symbol ("+") are new.
Lines starting with the tilde symbol ("~") are updated.

