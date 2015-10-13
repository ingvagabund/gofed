%define copying() \
%if 0%{?fedora} >= 21 || 0%{?rhel} >= 7 \
%license %{*} \
%else \
%doc %{*} \
%endif

%global _dwz_low_mem_die_limit 0
%global provider        github
%global provider_tld    com
%global project        	ingvagabund
%global repo            gofed
%global provider_prefix %{provider}.%{provider_tld}/%{project}/%{repo}
%global commit		2a3a173bd9c964efa848d6563b2aebe0f68d7e58
%global shortcommit	%(c=%{commit}; echo ${c:0:7})

Name:		gofed
Version:	0.0.8
Release:	0.1.git%{shortcommit}%{?dist}
Summary:	Tool for development of golang devel packages
License:	GPLv2+
URL:		https://github.com/%{project}/%{repo}
Source0:	https://github.com/%{project}/%{repo}/archive/%{commit}/%{repo}-%{shortcommit}.tar.gz
ExclusiveArch:  %{ix86} x86_64 %{arm}

BuildRequires: golang, python >= 2.7.5, python-lxml

Requires: python >= 2.7.5, bash, wget, rpmdevtools, rpmlint
Requires: fedpkg, koji, coreutils, rpm-build, openssh-clients, tar
Requires: bash-completion
Requires: python-lxml

%description
Tool to automize packaging of golang devel source codes.
The main goal is to automatize packaging, i.e. provide spec file generators,
discovery of tests, imported and provided packages,
check of up-to-date state of dependencies,
preparation of review and
check of spec file (gofed lint).

%package scan
Summary: Set of commands for scanning golang projects
Requires: %{name} = %{version}-%{release}
Requires: graphviz
BuildArch: noarch

%description scan
Subpackage providing commands for scanning of golang project, i.e.
comparison of APIs of two golang projects,
generator of xml files representing exported symbols and
scan of golang packages and generator of dependency graph.

%package build
Summary: Set of commands for building golang projects
Requires: %{name} = %{version}-%{release}
BuildArch: noarch

%description build
Subpackage providing commands for scratch builds, builds,
pulls, pushes, updates, overrides and other commands
that can be used for package maitainance.

The commands support running one command on multiple branches at once.

%package client
Summary: Set of commands for quering gofed-web server
Requires: %{name} = %{version}-%{release}
BuildArch: noarch

%description client
Subpackage providing commands for quering gofed-web server.

%prep
%setup -q -n %{repo}-%{commit}

%build
function gobuild { go build -a -ldflags "-B 0x$(head -c20 /dev/urandom|od -An -tx1|tr -d ' \n')" -v -x "$@"; }
gobuild parseGo.go

%install
# copy plugins
mkdir -p %{buildroot}/usr/share/%{name}/plugins
cp -pav plugins/*.json %{buildroot}/usr/share/%{name}/plugins
# copy bash completition
mkdir -p %{buildroot}%{_sysconfdir}/bash_completion.d/
python ./gen_bash_completion.py %{name} %{buildroot}/usr/share/%{name}/plugins "%{_sysconfdir}/bash_completion.d" plugins > %{buildroot}%{_sysconfdir}/bash_completion.d/%{name}
cp -pav plugins/*_bash_completion %{buildroot}%{_sysconfdir}/bash_completion.d/.
# copy man page
mkdir -p %{buildroot}%{_mandir}/man1
cp man/gofed-help.1 %{buildroot}/%{_mandir}/man1/gofed.1
# copy scripts
mkdir -p %{buildroot}/usr/share/%{name}
cp *.py %{buildroot}/usr/share/%{name}/.
cp -r modules %{buildroot}/usr/share/%{name}/.
cp parseGo %{buildroot}/usr/share/%{name}/.
# copy config
mkdir -p %{buildroot}%{_sysconfdir}/
cp config/gofed.conf %{buildroot}%{_sysconfdir}/.
# copy the tool script
cp %{name} %{buildroot}/usr/share/%{name}/.
# directory for local database
mkdir -p %{buildroot}%{_sharedstatedir}/%{name}
install -m 755 -d %{buildroot}/%{_sharedstatedir}/%{name}
install -m 755 -d %{buildroot}/usr/bin
# copy golang list and native imports
cp -r data %{buildroot}%{_sharedstatedir}/%{name}/.
ln -s /usr/share/%{name}/%{name} %{buildroot}/usr/bin/%{name}
# symlinks
cp -d build gcp pull push scratch-build update bbobranches bitbucket2gospec github2gospec googlecode2gospec %{buildroot}/usr/share/%{name}/.
# create directory for local repositories
install -m 0755 -d %{buildroot}%{_sharedstatedir}/%{name}/packages

%pre
getent group gofed >/dev/null || groupadd -r gofed
getent passwd gofed >/dev/null || useradd -r -g gofed -d / -s /sbin/nologin \
        -c "Gofed user" gofed
%files
%copying LICENSE
%doc *.md
%config(noreplace) /etc/gofed.conf
%{_sysconfdir}/bash_completion.d/%{name}
%{_sysconfdir}/bash_completion.d/gofed-base_bash_completion
%attr(0775, -, gofed) %{_sharedstatedir}/%{name}/packages
/usr/share/%{name}/plugins/gofed-base.json
/usr/share/%{name}/modules
/usr/share/%{name}/*.py*
/usr/share/%{name}/bbobranches
/usr/share/%{name}/build
/usr/share/%{name}/gcp
/usr/share/%{name}/gofed
/usr/share/%{name}/parseGo
/usr/share/%{name}/pull
/usr/share/%{name}/push
/usr/share/%{name}/scratch-build
/usr/share/%{name}/update
/usr/share/%{name}/bitbucket2gospec
/usr/share/%{name}/github2gospec
/usr/share/%{name}/googlecode2gospec
%{_mandir}/man1/gofed.1.gz
%{_sharedstatedir}/%{name}/data/golang.*
%{_sharedstatedir}/%{name}/data/repo.hints
/usr/bin/%{name}

%files scan
%{_sysconfdir}/bash_completion.d/gofed-scan_bash_completion
%{_sharedstatedir}/%{name}/data/pkgdb
%{_sharedstatedir}/%{name}/data/im_pr.packages
/usr/share/%{name}/plugins/gofed-scan.json

%files build
%{_sysconfdir}/bash_completion.d/gofed-build_bash_completion
/usr/share/%{name}/plugins/gofed-build.json

%files client
%{_sysconfdir}/bash_completion.d/gofed-client_bash_completion
/usr/share/%{name}/plugins/gofed-client.json

%check
export GOFED_TEST_CONFIG_FILE="1"
function gofed { %{buildroot}/usr/share/%{name}/%{name} "$@" --dry; }
gofed scratch-build
gofed build
gofed pull
gofed push
gofed update
gofed gcpmaster
gofed tools --git-reset
gofed tools --bbo --dry test
gofed tools --bbo --wait --dry test
gofed tools --waitbbo --dry test
gofed wizard --scratch --dry

%changelog
* Fri Sep 18 2015 fpokorny <fpokorny@redhat.com> - 0.0.8-0.1.git2a3a173
- Added client subpackage

* Thu Aug 20 2015 jchaloup <jchaloup@redhat.com> - 0.0.8-0.1.git2a3a173
- Bump to upstream 2a3a173bd9c964efa848d6563b2aebe0f68d7e58

* Sat Jul 11 2015 jchaloup <jchaloup@redhat.com> - 0.0.5-0.1.giteb25be8
- Initial commit for Fedora

