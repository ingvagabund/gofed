%global debug_package   %{nil}
%global provider        github
%global provider_tld    com
%global project        	ingvagabund
%global repo            gofed
%global commit		837cc974bd366a2093991a0edb6d3beb6b5b256e
%global shortcommit	%(c=%{commit}; echo ${c:0:7})

Name:		gofed
Version:	0
Release:	0.1.git%{shortcommit}%{?dist}
Summary:	Tool for development of golang devel packages
License:	GPLv2+
URL:		https://github.com/%{project}/%{repo}
Source0:	https://github.com/%{project}/%{repo}/archive/%{commit}/%{repo}-%{shortcommit}.tar.gz
ExclusiveArch:  %{ix86} x86_64 %{arm}

BuildRequires: golang
Requires: python >= 2.7.5, bash, wget, rpmdevtools, rpmlint
Requires: fedpkg, koji, coreutils, rpm-build, openssh-clients, tar
Requires: python-PyGithub, bash-completion
Requires: graphviz

%description
Tool to automize packaging of golang devel source codes.
The main goal is to automatize packaging (spec file generator),
dependency discovering, testing (scratch builds), to prepare package review.
If possible, all in one command.

%prep
%setup -q -n %{repo}-%{commit}

%build
go build parseGo.go

%install
# copy bash completition
mkdir -p %{buildroot}/etc/bash_completion.d/
./gen_bash_completion.sh %{name} > %{buildroot}/etc/bash_completion.d/%{name}
# copy man page
mkdir -p %{buildroot}/usr/share/man/man1
cp man/gofed-help.1 %{buildroot}/usr/share/man/man1/gofed.1
# copy scripts
mkdir -p %{buildroot}/usr/share/%{name}
cp *.sh %{buildroot}/usr/share/%{name}/.
cp *.py %{buildroot}/usr/share/%{name}/.
cp -r modules %{buildroot}/usr/share/%{name}/.
cp parseGo %{buildroot}/usr/share/%{name}/.
# copy config
mkdir -p %{buildroot}/usr/share/%{name}/config
cp config/gofed.conf %{buildroot}/usr/share/%{name}/config/.
# copy golang list and native imports
cp -r data %{buildroot}/usr/share/%{name}/.
# copy the tool script
cp %{name} %{buildroot}/usr/share/%{name}/.
# directory for local database
mkdir -p %{buildroot}/var/lib/%{name}
install -m 755 -d %{buildroot}/var/lib/%{name}

%post
if [ "$1" -eq 1 ]; then
	# make a symlink to gofed
	ln -s /usr/share/%{name}/%{name} /usr/bin/%{name}
fi

%preun
if [ "$1" -eq 0 ]; then
	rm /usr/bin/%{name}
fi

%files
%doc README.md LICENSE
%config /usr/share/%{name}/config/gofed.conf
/etc/bash_completion.d/%{name}
/usr/share/%{name}
/usr/share/man/man1/gofed.1.gz
/var/lib/%{name}

%changelog
* Mon Mar 23 2015 jchaloup <jchaloup@redhat.com> - 0-0.1.git3b5f081
- Initial commit for Fedora

