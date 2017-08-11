%{!?version: %define version 0.6.dev1}

%if 0%{?fedora} >= 26
%global with_python3 1
%endif

# FreeIPA up to 4.4.4 are not compatible with custodia because the custodia
# script now runs under Python 3. FreeIPA 4.4.5 and 4.4.4-2 on F26 are fixed.
%global ipa_version 4.4.4-2

Name:           custodia
Version:        %{version}
Release:        0%{?dist}
Summary:        A service to manage, retrieve and store secrets for other processes

License:        GPLv3+
URL:            https://github.com/latchset/%{name}
Source0:        https://github.com/latchset/%{name}/releases/download/v%{version}/%{name}-%{version}.tar.gz
Source2:        custodia.conf
Source3:        custodia@.service
Source4:        custodia@.socket
Source5:        custodia.tmpfiles.conf
Source6:        ipa.conf

BuildArch:      noarch

BuildRequires:      systemd
BuildRequires:      python2-devel
BuildRequires:      python2-jwcrypto >= 0.4.2
BuildRequires:      python2-requests
BuildRequires:      python2-setuptools >= 18
BuildRequires:      python2-coverage
BuildRequires:      python2-tox >= 2.3.1
BuildRequires:      python2-pytest
BuildRequires:      python2-mock
BuildRequires:      python2-python-etcd
BuildRequires:      python2-docutils
BuildRequires:      python2-configparser
BuildRequires:      python2-systemd
BuildRequires:      python2-ipaclient >= %{ipa_version}

%if 0%{?with_python3}
BuildRequires:      python%{python3_pkgversion}-devel
BuildRequires:      python%{python3_pkgversion}-jwcrypto >= 0.4.2
BuildRequires:      python%{python3_pkgversion}-requests
BuildRequires:      python%{python3_pkgversion}-setuptools > 18
BuildRequires:      python%{python3_pkgversion}-coverage
BuildRequires:      python%{python3_pkgversion}-tox >= 2.3.1
BuildRequires:      python%{python3_pkgversion}-pytest
BuildRequires:      python%{python3_pkgversion}-mock
BuildRequires:      python%{python3_pkgversion}-python-etcd
BuildRequires:      python%{python3_pkgversion}-docutils
BuildRequires:      python%{python3_pkgversion}-systemd
BuildRequires:      python%{python3_pkgversion}-ipaclient >= %{ipa_version}
%endif  # with_python3

%if 0%{?with_python3}
Requires:           python%{python3_pkgversion}-custodia = %{version}-%{release}
%else
Requires:           python2-custodia = %{version}-%{release}
%endif  # with_python3
Conflicts:          freeipa-server < %{ipa_version}
Requires(preun):    systemd-units
Requires(postun):   systemd-units
Requires(post):     systemd-units

%global overview                                                           \
Custodia is a Secrets Service Provider, it stores or proxies access to     \
keys, password, and secret material in general. Custodia is built to       \
use the HTTP protocol and a RESTful API as an IPC mechanism over a local   \
Unix Socket. It can also be exposed to a network via a Reverse Proxy       \
service assuming proper authentication and header validation is            \
implemented in the Proxy.                                                  \
                                                                           \
Custodia is modular, the configuration file controls how authentication,   \
authorization, storage and API plugins are combined and exposed.


%description
A service to manage, retrieve and store secrets for other processes

%{overview}

%package -n python2-custodia
Summary:    Sub-package with python2 custodia modules
%{?python_provide:%python_provide python2-%{name}}
Requires:   python2-configparser
Requires:   python2-jwcrypto >= 0.4.2
Requires:   python2-requests
Requires:   python2-setuptools
Requires:   python2-systemd


%description -n python2-custodia
Sub-package with python custodia modules

%{overview}

%package -n python2-custodia-extra
Summary:    Sub-package with python2 custodia extra modules
Requires:   python2-python-etcd
Requires:   python2-custodia = %{version}-%{release}

%description -n python2-custodia-extra
Sub-package with python2 custodia extra modules (etcdstore)

%{overview}

%package -n python2-custodia-ipa
Summary:    Sub-package with python2 custodia.ipa modules
%{?python_provide:%python_provide python2-custodia-ipa}
Requires:   python2-custodia = %{version}-%{release}
Requires:   python2-ipaclient >= %{ipa_version}

%description -n python2-custodia-ipa
custodia.ipa is a storage plugin for Custodia. It provides integration
with FreeIPA's vault facility. Secrets are encrypted and stored in
Dogtag's Key Recovery Agent.

%if 0%{?with_python3}
%package -n python%{python3_pkgversion}-custodia
Summary:    Sub-package with python3 custodia modules
%{?python_provide:%python_provide python3-%{name}}
Requires:   python%{python3_pkgversion}-jwcrypto >= 0.4.2
Requires:   python%{python3_pkgversion}-requests
Requires:   python%{python3_pkgversion}-setuptools
Requires:   python%{python3_pkgversion}-systemd

%description -n python%{python3_pkgversion}-custodia
Sub-package with python custodia modules

%{overview}

%package -n python%{python3_pkgversion}-custodia-extra
Summary:    Sub-package with python3 custodia extra modules
Requires:   python%{python3_pkgversion}-python-etcd
Requires:   python%{python3_pkgversion}-custodia = %{version}-%{release}

%description -n python%{python3_pkgversion}-custodia-extra
Sub-package with python3 custodia extra modules (etcdstore)

%{overview}

%if 0%{?with_ipa_python3}
%package -n python%{python3_pkgversion}-custodia-ipa
Summary:    Sub-package with python3 custodia.ipa modules
%{?python_provide:%python_provide python%{python3_pkgversion}-custodia-ipa}
Requires:   python%{python3_pkgversion}-custodia = %{version}-%{release}
Requires:   python%{python3_pkgversion}-ipaclient >= %{ipa_version}

%description -n python%{python3_pkgversion}-custodia-ipa
custodia.ipa is a storage plugin for Custodia. It provides integration
with FreeIPA's vault facility. Secrets are encrypted and stored in
Dogtag's Key Recovery Agent.

%endif  # wit_ipa_python3
%endif  # with_python3


%prep
%autosetup


%build
%py2_build
%if 0%{?with_python3}
%py3_build
%endif


%check
# don't download packages
export PIP_INDEX_URL=http://host.invalid./
# Don't try to download dnspython3. The package is provided by python3-dns
export PIP_NO_DEPS=yes
# Ignore all install packages to enforce installation of sdist. Otherwise tox
# may pick up this package from global site-packages instead of source dist.
export PIP_IGNORE_INSTALLED=yes

tox --sitepackages -e py%{python2_version_nodots} -- --skip-servertests
%if 0%{?with_python3}
tox --sitepackages -e py%{python3_version_nodots} -- --skip-servertests
%endif


%install
mkdir -p %{buildroot}/%{_sbindir}
mkdir -p %{buildroot}/%{_mandir}/man7
mkdir -p %{buildroot}/%{_defaultdocdir}/custodia
mkdir -p %{buildroot}/%{_defaultdocdir}/custodia/examples
mkdir -p %{buildroot}/%{_sysconfdir}/custodia
mkdir -p %{buildroot}/%{_unitdir}
mkdir -p %{buildroot}/%{_tmpfilesdir}
mkdir -p %{buildroot}/%{_localstatedir}/lib/custodia
mkdir -p %{buildroot}/%{_localstatedir}/log/custodia

%py2_install
mv %{buildroot}/%{_bindir}/custodia %{buildroot}/%{_sbindir}/custodia-2
mv %{buildroot}/%{_bindir}/custodia-cli %{buildroot}/%{_bindir}/custodia-cli-2
install -m 644 -t "%{buildroot}/%{_mandir}/man7" man/custodia.7
install -m 644 -t "%{buildroot}/%{_defaultdocdir}/custodia" README API.md
install -m 644 -t "%{buildroot}/%{_defaultdocdir}/custodia/examples" custodia.conf
install -m 600 %{SOURCE2} %{buildroot}%{_sysconfdir}/custodia
install -m 644 %{SOURCE3} %{buildroot}%{_unitdir}
install -m 644 %{SOURCE4} %{buildroot}%{_unitdir}
install -m 644 %{SOURCE5} %{buildroot}%{_tmpfilesdir}/custodia.conf
install -m 600 %{SOURCE6} %{buildroot}%{_sysconfdir}/custodia

%if 0%{?with_python3}
# overrides /usr/bin/custodia-cli and /usr/sbin/custodia with Python 3 shebang
%py3_install

%if ! 0%{?with_ipa_python3}
rm -rf %{buildroot}%{python3_sitelib}/custodia/ipa
%endif  # with_ipa_python3

mv %{buildroot}/%{_bindir}/custodia %{buildroot}/%{_sbindir}/custodia-3
mv %{buildroot}/%{_bindir}/custodia-cli %{buildroot}/%{_bindir}/custodia-cli-3
ln -sr %{buildroot}/%{_sbindir}/custodia-3 %{buildroot}/%{_sbindir}/custodia
ln -sr %{buildroot}/%{_bindir}/custodia-cli-3 %{buildroot}/%{_bindir}/custodia-cli
%else
ln -sr %{buildroot}/%{_sbindir}/custodia-2 %{buildroot}/%{_sbindir}/custodia
ln -sr %{buildroot}/%{_bindir}/custodia-cli-2 %{buildroot}/%{_bindir}/custodia-cli
%endif # with_python3


%pre
getent group custodia >/dev/null || groupadd -r custodia
getent passwd custodia >/dev/null || \
    useradd -r -g custodia -d / -s /sbin/nologin \
    -c "User for custodia" custodia
exit 0


%post
%systemd_post custodia@\*.socket
%systemd_post custodia@\*.service
%tmpfiles_create custodia.conf


%preun
%systemd_preun custodia@\*.socket
%systemd_preun custodia@\*.service


%postun
%systemd_postun custodia@\*.socket
%systemd_postun custodia@\*.service


%files
%doc README API.md
%doc %{_defaultdocdir}/custodia/examples/custodia.conf
%license LICENSE
%{_mandir}/man7/custodia*
%{_sbindir}/custodia
%{_bindir}/custodia-cli
%dir %attr(0700,custodia,custodia) %{_sysconfdir}/custodia
%config(noreplace) %attr(600,custodia,custodia) %{_sysconfdir}/custodia/custodia.conf
%config(noreplace) %attr(600,custodia,custodia) %{_sysconfdir}/custodia/ipa.conf
%attr(644,root,root)  %{_unitdir}/custodia@.socket
%attr(644,root,root)  %{_unitdir}/custodia@.service
%dir %attr(0700,custodia,custodia) %{_localstatedir}/lib/custodia
%dir %attr(0700,custodia,custodia) %{_localstatedir}/log/custodia
%{_tmpfilesdir}/custodia.conf

%files -n python2-custodia
%license LICENSE
%exclude %{python2_sitelib}/custodia/ipa
%exclude %{python2_sitelib}/custodia/store/etcdstore.py*
%{python2_sitelib}/%{name}
%{python2_sitelib}/%{name}-%{version}-py%{python2_version}.egg-info
%{python2_sitelib}/%{name}-%{version}-py%{python2_version}-nspkg.pth
%{_sbindir}/custodia-2
%{_bindir}/custodia-cli-2

%files -n python2-custodia-extra
%license LICENSE
%{python2_sitelib}/custodia/store/etcdstore.py*

%files -n python2-custodia-ipa
%license LICENSE
%{python2_sitelib}/custodia/ipa

%if 0%{?with_python3}
%files -n python%{python3_pkgversion}-custodia
%license LICENSE
%exclude %{python3_sitelib}/custodia/ipa
%exclude %{python3_sitelib}/custodia/store/etcdstore.py
%exclude %{python3_sitelib}/custodia/store/__pycache__/etcdstore.*
%{python3_sitelib}/%{name}
%{python3_sitelib}/%{name}-%{version}-py%{python3_version}.egg-info
%{python3_sitelib}/%{name}-%{version}-py%{python3_version}-nspkg.pth
%{_sbindir}/custodia-3
%{_bindir}/custodia-cli-3

%files -n python%{python3_pkgversion}-custodia-extra
%license LICENSE
%{python3_sitelib}/custodia/store/etcdstore.py
%{python3_sitelib}/custodia/store/__pycache__/etcdstore.*

%if 0%{?with_ipa_python3}
%files -n python%{python3_pkgversion}-custodia-ipa
%license LICENSE
%{python3_sitelib}/custodia/ipa
%endif  # with_ipa_python3

%endif  # with_python3
