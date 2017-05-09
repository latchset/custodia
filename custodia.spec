%if 0%{?fedora}
%global with_python3 1
%global with_etcdstore 1
%endif

%{!?version: %define version 0.3.1}

Name:           custodia
Version:        %{version}
Release:        3%{?dist}
Summary:        A service to manage, retrieve and store secrets for other processes

License:        GPLv3+
URL:            https://github.com/latchset/%{name}
Source0:        https://github.com/latchset/%{name}/releases/download/v%{version}/%{name}-%{version}.tar.gz
Source1:        https://github.com/latchset/%{name}/releases/download/v%{version}/%{name}-%{version}.tar.gz.sha512sum.txt
Source2:        custodia.conf
Source3:        custodia.service
Source4:        custodia.socket
Source5:        custodia.tmpfiles.conf

BuildArch:      noarch

BuildRequires:      python2-devel
BuildRequires:      python-jwcrypto
BuildRequires:      python2-requests
BuildRequires:      python2-setuptools >= 18
BuildRequires:      python2-coverage
BuildRequires:      python-tox >= 2.3.1
BuildRequires:      python2-pytest
BuildRequires:      python-docutils
BuildRequires:      python2-configparser
BuildRequires:      python2-systemd
%if 0%{?with_etcdstore}
BuildRequires:      python2-python-etcd
%endif

%if 0%{?with_python3}
BuildRequires:      python3-devel
BuildRequires:      python3-jwcrypto
BuildRequires:      python3-requests
BuildRequires:      python3-setuptools > 18
BuildRequires:      python3-coverage
BuildRequires:      python3-tox >= 2.3.1
BuildRequires:      python3-pytest
BuildRequires:      python3-python-etcd
BuildRequires:      python3-docutils
BuildRequires:      python3-systemd
%endif

Requires(pre):      shadow-utils

%if 0%{?with_python3}
Requires:           python3-custodia = %{version}-%{release}
%else
Requires:           python2-custodia = %{version}-%{release}
%endif

# FreeIPA 4.3 and 4.4 are not compatible with custodia because the custodia
# script now runs under Python 3.
Conflicts:          freeipa-server-common < 4.5
Conflicts:          ipa-server-common < 4.5

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
Provides:   python-custodia = %{version}-%{release}
Obsoletes:  python-custodia <= 0.1.0
Requires:   python2-configparser
Requires:   python-jwcrypto
Requires:   python2-requests
Requires:   python2-setuptools
Requires:   python2-systemd
Conflicts:  python2-ipalib < 4.5

%description -n python2-custodia
Sub-package with python custodia modules

%{overview}

%if 0%{?with_etcdstore}
%package -n python2-custodia-etcdstore
Summary:    Sub-package with python2 custodia etcdstore
Requires:   python2-python-etcd
Requires:   python2-custodia = %{version}-%{release}
Obsoletes:  python2-custodia-extras <= 0.3.1

%description -n python2-custodia-etcdstore
Sub-package with python2 custodia etcdstore plugin

%{overview}
%endif  # with_etcdstore

%if 0%{?with_python3}
%package -n python3-custodia
Summary:    Sub-package with python3 custodia modules
Requires:   python3-jwcrypto
Requires:   python3-requests
Requires:   python3-setuptools
Requires:   python3-systemd
Conflicts:  python3-ipalib < 4.5

%description -n python3-custodia
Sub-package with python custodia modules

%{overview}

%if 0%{?with_etcdstore}
%package -n python3-custodia-etcdstore
Summary:    Sub-package with python3 custodia etcdstoore
Requires:   python3-python-etcd
Requires:   python3-custodia = %{version}-%{release}
Obsoletes:  python3-custodia-extras <= 0.3.1

%description -n python3-custodia-etcdstore
Sub-package with python3 custodia extra etcdstore plugin

%{overview}

%endif  # with_etcdstore
%endif  # with_python3


%prep
grep `sha512sum %{SOURCE0}` %{SOURCE1} || (echo "Checksum invalid!" && exit 1)
%autosetup


%build
%{__python2} setup.py egg_info build
%if 0%{?with_python3}
%{__python3} setup.py egg_info build
%endif


%check
# don't download packages
export PIP_INDEX_URL=http://host.invalid./
# Don't try to download dnspython3. The package is provided by python3-dns
export PIP_NO_DEPS=yes

tox --sitepackages -e py27 -- --skip-servertests
%if 0%{?with_python3}
TOXENV=$(%{__python3} -c 'import sys; print("py{0.major}{0.minor}".format(sys.version_info))')
tox --sitepackages -e $TOXENV -- --skip-servertests
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

%{__python2} setup.py install --skip-build --root %{buildroot}
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
%{__python3} setup.py install --skip-build --root %{buildroot}
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


%files
%doc README API.md
%doc %{_defaultdocdir}/custodia/examples/custodia.conf
%license LICENSE
%{_mandir}/man7/custodia*
%{_sbindir}/custodia
%{_bindir}/custodia-cli
%dir %attr(0700,custodia,custodia) %{_sysconfdir}/custodia
%config(noreplace) %attr(600,custodia,custodia) %{_sysconfdir}/custodia/custodia.conf
%attr(644,root,root)  %{_unitdir}/custodia.socket
%attr(644,root,root)  %{_unitdir}/custodia.service
%dir %attr(0700,custodia,custodia) %{_localstatedir}/lib/custodia
%dir %attr(0700,custodia,custodia) %{_localstatedir}/log/custodia
%dir %attr(0755,custodia,custodia) %{_localstatedir}/run/custodia
%{_tmpfilesdir}/custodia.conf

%files -n python2-custodia
%license LICENSE
%exclude %{python2_sitelib}/custodia/store/etcdstore.py*
%{python2_sitelib}/*
%{_sbindir}/custodia-2
%{_bindir}/custodia-cli-2

%if 0%{?with_etcdstore}
%files -n python2-custodia-etcdstore
%license LICENSE
%{python2_sitelib}/custodia/store/etcdstore.py*
%endif  # with_etcdstore

%if 0%{?with_python3}
%files -n python3-custodia
%license LICENSE
%exclude %{python3_sitelib}/custodia/store/etcdstore.py
%exclude %{python3_sitelib}/custodia/store/__pycache__/etcdstore.*
%{python3_sitelib}/*
%{_sbindir}/custodia-3
%{_bindir}/custodia-cli-3

%if 0%{?with_etcdstore}
%files -n python3-custodia-etcdstore
%license LICENSE
%{python3_sitelib}/custodia/store/etcdstore.py
%{python3_sitelib}/custodia/store/__pycache__/etcdstore.*
%endif  # with_etcdstore
%endif  # with_python3

