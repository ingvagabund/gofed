#!/bin/sh

# ####################################################################
# gofed - set of tools to automize packaging of golang devel codes
# Copyright (C) 2014  Jan Chaloupka, jchaloup@redhat.com
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
# ####################################################################

if [ "$#" -ne 3 ]; then
	echo "Error: Wrong number of parameters."
	echo "Synopsis: $0 PROJECT REPO COMMIT"
	exit 0
fi

project=$1
repo=$2
provider='bitbucket'
provider_tld='org'
commit=$3
shortcommit=${commit:0:12}
script_dir=$(dirname $0)

red='\e[0;31m'
orange='\e[0;33m'
NC='\e[0m'

total=4

echo -e "${orange}Repo URL:$NC"
echo "https://$provider.$provider_tld/$project/$repo"
echo ""
# prepare basic structure
name=golang-$provider-$project-$repo

echo -e "${orange}(1/$total) Checking if the package already exists in PkgDB$NC"
git ls-remote "http://pkgs.fedoraproject.org/cgit/$name.git/" 2>/dev/null 1>&2

if [ "$?" -eq 0 ]; then
	echo -e "$red\tPackage already exists$NC"
	exit 0
fi

# creating basic folder structure
mkdir -p $name/fedora/$name
cd $name/fedora/$name

echo -e "${orange}(2/$total) Downloading tarball$NC"
download=$(wget -nv https://bitbucket.org/$project/$repo/get/$shortcommit.zip 2>&1)
if [ "$?" -ne 0 ]; then
	echo "	Unable to download the tarball"
	echo "	$download"
	exit
fi

unzip -q $shortcommit.zip

echo -e "${orange}(3/$total) Creating spec file$NC"
# creating spec file
specfile=$name".spec"
echo "%global debug_package   %{nil}" > $specfile
echo "%global provider        $provider" >> $specfile
echo "%global provider_tld    $provider_tld" >> $specfile
echo "%global project         $project" >> $specfile
echo "%global repo            $repo" >> $specfile
echo "# https://$provider.$provider_tld/$project/$repo" >> $specfile
echo "%global import_path     %{provider}.%{provider_tld}/%{project}/%{repo}" >> $specfile
echo "%global commit          $commit" >> $specfile
echo "%global shortcommit     %(c=%{commit}; echo \${c:0:12})" >> $specfile
echo "" >> $specfile
echo "Name:           golang-%{provider}-%{project}-%{repo}" >> $specfile
echo "Version:        0" >> $specfile
echo "Release:        0.0.git%{shortcommit}%{?dist}" >> $specfile
echo "Summary:        !!!!FILL!!!!" >> $specfile
echo "License:        !!!!FILL!!!!" >> $specfile
echo "URL:            https://%{import_path}" >> $specfile
echo "Source0:        https://%{import_path}/get/%{shortcommit}.zip" >> $specfile
echo "%if 0%{?fedora} >= 19 || 0%{?rhel} >= 7" >> $specfile
echo "BuildArch:      noarch" >> $specfile
echo "%else" >> $specfile
echo "ExclusiveArch:  %{ix86} x86_64 %{arm}" >> $specfile
echo "%endif" >> $specfile
echo "" >> $specfile
echo "%description" >> $specfile
echo "%{summary}" >> $specfile
echo "" >> $specfile
echo "%package devel" >> $specfile
echo "BuildRequires:  golang >= 1.2.1-3" >> $specfile

# get relevant golang imports (still does not have to be correct)
deps=$(python $script_dir/ggi.py | grep -v "$provider.$provider_tld/$project/$repo")
for gimport in $deps; do
	echo "BuildRequires:  golang($gimport)" >> $specfile
done

echo "Requires:       golang >= 1.2.1-3" >> $specfile
for gimport in $deps; do
	echo "Requires:       golang($gimport)" >> $specfile
done

echo "Summary:        %{summary}" >> $specfile
# list Provides section
for dir in $(python $script_dir/inspecttarball.py -p $project-$repo-$shortcommit | sort); do
	sufix=""
	if [ "$dir" != "." ]; then
		sufix="/$dir"
	fi

	echo "Provides:       golang(%{import_path}$sufix) = %{version}-%{release}" >> $specfile
done

echo "" >> $specfile
echo "%description devel" >> $specfile
echo "%{summary}" >> $specfile
echo "" >> $specfile
echo "This package contains library source intended for " >> $specfile
echo "building other packages which use %{project}/%{repo}." >> $specfile
echo "" >> $specfile
echo "%prep" >> $specfile
echo "%setup -q -n %{project}-%{repo}-%{shortcommit}" >> $specfile
echo "" >> $specfile
echo "%build" >> $specfile
echo "" >> $specfile
echo "%install" >> $specfile
echo "install -d -p %{buildroot}/%{gopath}/src/%{import_path}/" >> $specfile

ls $project-$repo-$shortcommit/*.go 1>/dev/null 2>/dev/null
if [ "$?" -eq 0 ]; then
	echo "cp -pav *.go %{buildroot}/%{gopath}/src/%{import_path}/" >> $specfile
fi

# read all dirs in the tarball
for dir in $(python $script_dir/inspecttarball.py -d $project-$repo-$shortcommit); do
	echo "cp -rpav $dir %{buildroot}/%{gopath}/src/%{import_path}/" >> $specfile
done

echo "" >> $specfile
echo "%check" >> $specfile

# get all dirs containing test files
for dir in $(python $script_dir/inspecttarball.py -t $project-$repo-$shortcommit); do
	sufix="/$dir"
	if [ "$dir" == "." ]; then
		sufix=""
	fi
	echo "GOPATH=%{buildroot}/%{gopath}:%{gopath} go test %{import_path}$sufix" >> $specfile
done

echo "" >> $specfile
echo "%files devel" >> $specfile
# doc all *.md files
docs=""
pushd $project-$repo-$shortcommit 1>/dev/null
ls *.md 1>/dev/null 2>/dev/null
if [ "$?" -eq 0 ]; then
	docs="$docs $(echo -n $(ls *.md))"
fi
ls LICENSE 1>/dev/null 2>/dev/null
if [ "$?" -eq 0 ]; then
        docs="$docs LICENSE"
fi
ls README 1>/dev/null 2>/dev/null
if [ "$?" -eq 0 ]; then
        docs="$docs README"
fi
ls AUTHORS 1>/dev/null 2>/dev/null
if [ "$?" -eq 0 ]; then
        docs="$docs AUTHORS"
fi
popd >/dev/null

echo "%doc$docs" >> $specfile
echo "%dir %{gopath}/src/%{provider}.%{provider_tld}/%{project}" >> $specfile
# http://www.rpm.org/max-rpm/s1-rpm-inside-files-list-directives.html
# it takes every dir and file recursively
echo "%{gopath}/src/%{import_path}" >> $specfile
echo "" >> $specfile
echo "%changelog" >> $specfile
echo "" >> $specfile

rpmdev-bumpspec $specfile -c "First package for Fedora"


echo -e "${orange}(4/$total) Discovering golang dependencies$NC"
cd $project-$repo-$shortcommit
python $script_dir/ggi.py -c -s -d | grep -v $name

cd ..

echo ""
echo -e "${orange}Spec file $name.spec at:$NC"
pwd

