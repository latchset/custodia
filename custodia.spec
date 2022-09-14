%if 0%{?fedora}
%global with_python3 1
%endif

%{!?version: %define version 0.7.dev1}

# FreeIPA up to 4.4.4 are not compatible with custodia because the custodia
# script now runs under Python 3. FreeIPA 4.4.5 and 4.4.4-2 on F26 are fixed.
# ipa_conflict is used with '<' version comparison.
%if 0%{?fedora} >= 26
%global ipa_conflict 4.4.4-2
%else
%global ipa_conflict 4.4.5
%endif

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

BuildArch:      noarch

BuildRequires:      systemd
BuildRequires:      python2-devel
BuildRequires:      python2-jwcrypto >= 1.4.0
BuildRequires:      python2-requests
BuildRequires:      python2-setuptools >= 18
BuildRequires:      python2-coverage
BuildRequires:      python2-tox >= 2.3.1
BuildRequires:      python2-pytest
BuildRequires:      python2-docutils
BuildRequires:      python2-configparser
BuildRequires:      python2-systemd

%if 0%{?with_python3}
BuildRequires:      python%{python3_pkgversion}-devel
BuildRequires:      python%{python3_pkgversion}-jwcrypto >= 1.4.0
BuildRequires:      python%{python3_pkgversion}-requests
BuildRequires:      python%{python3_pkgversion}-setuptools > 18
BuildRequires:      python%{python3_pkgversion}-coverage
BuildRequires:      python%{python3_pkgversion}-tox >= 2.3.1
BuildRequires:      python%{python3_pkgversion}-pytest
BuildRequires:      python%{python3_pkgversion}-docutils
BuildRequires:      python%{python3_pkgversion}-systemd
%endif

%if 0%{?with_python3}
Requires:           python%{python3_pkgversion}-custodia = %{version}-%{release}
%else
Requires:           python2-custodia = %{version}-%{release}
%endif

Requires(preun):    systemd-units
Requires(postun):   systemd-units
Requires(post):     systemd-units

Conflicts:          freeipa-server-common < %{ipa_conflict}
Conflicts:          ipa-server-common < %{ipa_conflict}


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
Requires:   python2-jwcrypto > 1.4.0
Requires:   python2-requests
Requires:   python2-setuptools
Requires:   python2-systemd
Conflicts:  python2-ipalib < %{ipa_conflict}

%description -n python2-custodia
Sub-package with python custodia modules

%{overview}

%if 0%{?with_python3}
%package -n python%{python3_pkgversion}-custodia
Summary:    Sub-package with python3 custodia modules
%{?python_provide:%python_provide python3-%{name}}
Requires:   python%{python3_pkgversion}-jwcrypto >= 1.4.0
Requires:   python%{python3_pkgversion}-requests
Requires:   python%{python3_pkgversion}-setuptools
Requires:   python%{python3_pkgversion}-systemd
Conflicts:  python%{python3_pkgversion}-ipalib < %{ipa_conflict}

%description -n python%{python3_pkgversion}-custodia
Sub-package with python custodia modules

%{overview}

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
# Don't try to download dnspython3. The package is provided by python%{python3_pkgversion}-dns
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
mkdir -p %{buildroot}/%{_localstatedir}/run/custodia

%py2_install
mv %{buildroot}/%{_bindir}/custodia %{buildroot}/%{_sbindir}/custodia
cp %{buildroot}/%{_sbindir}/custodia %{buildroot}/%{_sbindir}/custodia-2
cp %{buildroot}/%{_bindir}/custodia-cli %{buildroot}/%{_bindir}/custodia-cli-2
install -m 644 -t "%{buildroot}/%{_mandir}/man7" man/custodia.7
install -m 644 -t "%{buildroot}/%{_defaultdocdir}/custodia" README API.md
install -m 644 -t "%{buildroot}/%{_defaultdocdir}/custodia/examples" custodia.conf
install -m 600 %{SOURCE2} %{buildroot}%{_sysconfdir}/custodia
install -m 644 %{SOURCE3} %{buildroot}%{_unitdir}
install -m 644 %{SOURCE4} %{buildroot}%{_unitdir}
install -m 644 %{SOURCE5} %{buildroot}%{_tmpfilesdir}/custodia.conf

%if 0%{?with_python3}
# overrides /usr/bin/custodia-cli and /usr/sbin/custodia with Python 3 shebang
%py3_install
mv %{buildroot}/%{_bindir}/custodia %{buildroot}/%{_sbindir}/custodia
cp %{buildroot}/%{_sbindir}/custodia %{buildroot}/%{_sbindir}/custodia-3
cp %{buildroot}/%{_bindir}/custodia-cli %{buildroot}/%{_bindir}/custodia-cli-3
%endif


%pre
getent group custodia >/dev/null || groupadd -r custodia
getent passwd custodia >/dev/null || \
    useradd -r -g custodia -d / -s /sbin/nologin \
    -c "User for custodia" custodia
exit 0


%post
%systemd_post custodia@\*.socket
%systemd_post custodia@\*.service


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
%attr(644,root,root)  %{_unitdir}/custodia@.socket
%attr(644,root,root)  %{_unitdir}/custodia@.service
%dir %attr(0700,custodia,custodia) %{_localstatedir}/lib/custodia
%dir %attr(0700,custodia,custodia) %{_localstatedir}/log/custodia
%dir %attr(0755,custodia,custodia) %{_localstatedir}/run/custodia
%{_tmpfilesdir}/custodia.conf

%files -n python2-custodia
%license LICENSE
%{python2_sitelib}/%{name}
%{python2_sitelib}/%{name}-%{version}-py%{python2_version}.egg-info
%{python2_sitelib}/%{name}-%{version}-py%{python2_version}-nspkg.pth
%{_sbindir}/custodia-2
%{_bindir}/custodia-cli-2

%if 0%{?with_python3}
%files -n python%{python3_pkgversion}-custodia
%license LICENSE
%{python3_sitelib}/%{name}
%{python3_sitelib}/%{name}-%{version}-py%{python3_version}.egg-info
%{python3_sitelib}/%{name}-%{version}-py%{python3_version}-nspkg.pth
%{_sbindir}/custodia-3
%{_bindir}/custodia-cli-3

%endif  # with_python3
