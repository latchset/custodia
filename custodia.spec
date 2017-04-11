%if 0%{?fedora}
%global with_python3 1
%endif

Name:           custodia
Version:        0.3.1
Release:        2%{?dist}
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
BuildRequires:      python2-python-etcd
BuildRequires:      python-docutils
BuildRequires:      python2-configparser
BuildRequires:      python2-systemd

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


%package -n python2-custodia-extra
Summary:    Sub-package with python2 custodia extra modules
Requires:   python2-python-etcd
Requires:   python2-custodia = %{version}-%{release}

%description -n python2-custodia-extra
Sub-package with python2 custodia extra modules (etcdstore)

%{overview}


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


%package -n python3-custodia-extra
Summary:    Sub-package with python3 custodia extra modules
Requires:   python3-python-etcd
Requires:   python3-custodia = %{version}-%{release}

%description -n python3-custodia-extra
Sub-package with python3 custodia extra modules (etcdstore)

%{overview}

%endif


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
tox --sitepackages -e py35 -- --skip-servertests
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


%files
%doc README API.md
%doc %{_defaultdocdir}/custodia/examples/custodia.conf
%license LICENSE
%{_mandir}/man7/custodia*
%{_sbindir}/custodia
%{_bindir}/custodia-cli
%dir %attr(0700,root,root) %{_sysconfdir}/custodia
%config(noreplace) %attr(600,root,root) %{_sysconfdir}/custodia/custodia.conf
%attr(644,root,root)  %{_unitdir}/custodia.socket
%attr(644,root,root)  %{_unitdir}/custodia.service
%dir %attr(0700,root,root) %{_localstatedir}/lib/custodia
%dir %attr(0700,root,root) %{_localstatedir}/log/custodia
%{_tmpfilesdir}/custodia.conf

%files -n python2-custodia
%license LICENSE
%exclude %{python2_sitelib}/custodia/store/etcdstore.py*
%{python2_sitelib}/*
%{_sbindir}/custodia-2
%{_bindir}/custodia-cli-2

%files -n python2-custodia-extra
%license LICENSE
%{python2_sitelib}/custodia/store/etcdstore.py*

%if 0%{?with_python3}
%files -n python3-custodia
%license LICENSE
%exclude %{python3_sitelib}/custodia/store/etcdstore.py
%exclude %{python3_sitelib}/custodia/store/__pycache__/etcdstore.*
%{python3_sitelib}/*
%{_sbindir}/custodia-3
%{_bindir}/custodia-cli-3

%files -n python3-custodia-extra
%license LICENSE
%{python3_sitelib}/custodia/store/etcdstore.py
%{python3_sitelib}/custodia/store/__pycache__/etcdstore.*
%endif


%changelog
* Fri Apr 07 2017 Christian Heimes <cheimes@redhat.com> - 0.3.1-2
- Add conflict with FreeIPA < 4.5

* Mon Mar 27 2017 Christian Heimes <cheimes@redhat.com> - 0.3.1-1
- Upstream release 0.3.1

* Thu Mar 16 2017 Christian Heimes <cheimes@redhat.com> - 0.3.0-3
- Provide custodia-2 and custodia-3 scripts

* Thu Mar 02 2017 Christian Heimes <cheimes@redhat.com> - 0.3.0-2
- Run Custodia daemon with Python 3
- Resolves: Bug 1426737 - custodia: Provide a Python 3 subpackage

* Wed Mar 01 2017 Christian Heimes <cheimes@redhat.com> - 0.3.0-1
- Update to custodia 0.3.0
- Run tests with global site packages
- Add tmpfiles.d config for /run/custodia

* Wed Feb 22 2017 Christian Heimes <cheimes@redhat.com> - 0.2.0-4
- Add missing runtime requirement on python[23]-systemd.
- Drop unnecesary build dependency on python3-configparser.
- Fix tests, don't try to download dnspython3.

* Fri Feb 10 2017 Fedora Release Engineering <releng@fedoraproject.org> - 0.2.0-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_26_Mass_Rebuild

* Thu Dec 22 2016 Miro Hrončok <mhroncok@redhat.com> - 0.2.0-2
- Rebuild for Python 3.6

