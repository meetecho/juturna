# Security Policy

This document explains how security vulnerabilities affecting **Juturna**
(https://github.com/meetecho/juturna) are reported, handled and disclosed.

Meetecho acts as **open-source software steward** of Juturna under
Regulation (EU) 2024/2847 on horizontal cybersecurity requirements for
products with digital elements (the "Cyber Resilience Act", CRA). This
policy is put in place and documented pursuant to **Article 24(1) CRA**,
to foster the development of a secure product, an effective handling of
vulnerabilities by Juturna's developers and users, and the voluntary
reporting of vulnerabilities referred to in Article 15 CRA.

This policy is not legal advice. It does not, by itself, determine
Meetecho's or any contributor's regulatory status under the CRA for a
specific deployment of Juturna.

## 1. Scope

This policy covers security vulnerabilities in:

- the Juturna Python library (source code hosted in this repository);
- official plugins and nodes distributed through the Juturna hub under
  the `meetecho` organisation;
- the packaging, build and release pipeline (CI/CD, Dockerfile, published
  packages) used to distribute Juturna.

Out of scope:

- vulnerabilities in third-party dependencies, which should be reported
  upstream (see [Section 6](#6-third-party-components));
- vulnerabilities in downstream applications or deployments built on top
  of Juturna, unless the root cause is in Juturna itself;
- denial-of-service testing, load testing or automated scanning done
  without prior coordination with the maintainers;
- social engineering or physical attacks against Meetecho's staff,
  infrastructure or premises.

## 2. Supported versions

Security fixes are provided, on a best-effort basis, for:

| Version                          | Supported |
| --------------------------------- | :-------: |
| `main` (latest development)       | ✅        |
| Latest major release              | ✅        |
| Previous LTS release (if any)     | ✅        |
| Older / unmaintained releases     | ❌        |

Juturna follows [Semantic Versioning](https://semver.org). Supported
release lines are also listed in `CHANGELOG.md`. The project is still
evolving toward production-readiness (see `README.md`), so the set of
actively patched versions may change between minor releases. This table
is kept up to date.

## 3. How to report a vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Report a vulnerability through either of these channels:

- **GitHub Security Advisories**: use the "Report a vulnerability" button
  under the [Security tab](https://github.com/meetecho/juturna/security/advisories/new)
  of this repository. This is the preferred channel, since it creates a
  private advisory and lets us coordinate a fix with you directly on
  GitHub.
- **Email**: `security@meetecho.com`.

Reports may be submitted in **English or Italian**.

Please include, where possible:

- affected version(s) or commit hash;
- a clear description of the vulnerability and its potential impact;
- step-by-step reproduction instructions or a proof of concept;
- any known mitigations.

### What you can expect from us

Juturna is maintained by a small open-source team. We do not commit to a
fixed SLA, but we handle reports on a best-effort basis and aim to:

- acknowledge receipt of your report;
- keep you informed as we investigate, triage and work on a fix;
- credit you (unless you prefer to remain anonymous) once the issue is
  publicly disclosed.

## 4. Coordinated disclosure

We follow a coordinated (responsible) disclosure process:

1. **Triage**: we assess severity, scope and affected versions.
2. **Fix**: we develop and test a patch, in private, together with the
   reporter where useful.
3. **Release**: the fix is published in a new Juturna release, along
   with a GitHub Security Advisory describing the issue (using a CVE
   identifier where applicable).
4. **Public disclosure**: technical details are published only after a
   fix (or documented mitigation) is available, in line with standard
   coordinated vulnerability disclosure (CVD) practice and Article 24(1)
   CRA.

We ask reporters to keep vulnerability details confidential until a fix
is released, and not to exploit the vulnerability beyond what is
necessary to demonstrate it (proof of concept only, no data
exfiltration, no service disruption). Good-faith security research
conducted in line with this policy will not be treated as a hostile act
by Meetecho.

## 5. Sharing information with the community

In line with Article 24(1) CRA, once a fix is released we:

- publish a Security Advisory on this repository describing the
  vulnerability, its impact and the affected versions;
- document the fix in `CHANGELOG.md`;
- where relevant, share information with other affected open-source
  projects or with public vulnerability databases (e.g. the [GitHub
  Advisory Database](https://github.com/advisories), CVE, OSV) so the
  wider community can benefit.

## 6. Third-party components

Juturna depends on third-party Python packages. Vulnerabilities in those
dependencies should be reported directly to the relevant upstream
project. We monitor our dependency tree (via `pyproject.toml`, `bandit`,
dependency-scanning tooling) and update vulnerable dependencies as fixes
become available. You are welcome to flag an outdated or vulnerable
dependency through the channels in Section 3.

## 7. Cooperation with market surveillance authorities

In accordance with **Article 24(2) CRA**, Meetecho, as open-source
software steward of Juturna, will cooperate with competent market
surveillance authorities, at their reasoned request, with a view to
mitigating cybersecurity risks posed by Juturna. Upon such a reasoned
request, the documentation referred to in Sections 1 to 6 of this policy
will be made available, in paper or electronic form, in a language that
can be easily understood by the requesting authority.

## 8. Safe harbour for researchers

We will not pursue legal action against security researchers who:

- act in good faith and in accordance with this policy;
- make a reasonable, good-faith effort to avoid privacy violations,
  degradation of service, or destruction of data;
- report vulnerabilities exclusively through the channels above and do
  not disclose them publicly before a fix is available;
- do not exploit a vulnerability beyond what is necessary to demonstrate
  it.

## 9. Changes to this policy

This policy is reviewed periodically and may be updated to reflect
changes in the project, in applicable regulation (including future
implementing or delegated acts under the CRA), or in our processes. See
the Git history of this file for prior versions.

---

Last updated: [DATE]. Maintained by Meetecho as open-source software
steward of Juturna, pursuant to Article 24 of Regulation (EU) 2024/2847.
