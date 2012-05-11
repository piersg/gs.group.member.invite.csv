# coding=utf-8
import os
from setuptools import setup, find_packages
from version import get_version

version = get_version()

setup(name='gs.group.member.invite.csv',
    version=version,
    description="Invite people to a group using a CSV file",
    long_description=open("README.txt").read() + "\n" +
                    open(os.path.join("docs", "HISTORY.txt")).read(),
    classifiers=[
      "Development Status :: 4 - Beta",
      "Environment :: Web Environment",
      "Framework :: Zope2",
      "Intended Audience :: Developers",
      "License :: Other/Proprietary License",
      "Natural Language :: English",
      "Operating System :: POSIX :: Linux"
      "Programming Language :: Python",
      "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords='sign up, registration, profile, user, join, invitation',
    author='Richard Waid',
    author_email='richard@onlinegroups.net',
    url='http://groupserver.org',
    license='ZPL',
    packages=find_packages(exclude=['ez_setup']),
    namespace_packages=['gs', 'gs.group', 'gs.group.member', 'gs.group.member.invite'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'setuptools',
        'gs.content.form',
        'gs.group.member.base',
        'gs.help',
        'gs.profile.email.base',
        'gs.profile.notify',
        'gs.site.member',
        'Products.GSProfile',
        'Products.XWFCore',
        'Products.CustomUserFolder'
        # -*- Extra requirements: -*-
    ],
    entry_points="""
    # -*- Entry points: -*-
    """,
)

