.. sectnum::

============
Introduction
============

The ``gs.group.member.invite`` module is concerned with the *issuing*
of invitations to join an online group. Invitations take the form of
an email message with a link. The invitation is responded to using one
of the two pages in the ``gs.profile.invite`` module.

Why Invitations?
================

Why does GroupServer insist in sending invitations rather than allowing
an administrator to *just add* members? Good question.

For new members the invitation does two things in addition to joining
a person to a group. First, it **verifies** that the email address
works. Unless the address is verified messages will not be sent to
it. Second, the Respond page allows the member to set a password,
so he or she is able to log in.

Even for people that already have profiles, the invitations also allow
*informed consent*. This is not just a good idea, in many countries it
is the law.

Pages
=====

There are three pages used for issuing invitations:

* `Invite Site Member`_
* `Invite New Member`_ and
* `Send Invitations in Bulk`_

All the pages for issuing an invitation are located in the group, and
are attached to the group maker-interface.

Invite Site Member
------------------

The page for inviting a site member to join a group is the simplest. It
uses a vocabulary to list all the site members who are not members of
the group. The administrator selects the site members to be invited,
and issues an invitation to them.

Invite New Member
-----------------

The most commonly used invitation page is used to invite a single person
to join a group. This page allows the administrator to do the following.

1. Create a complete profile for the new member, including an email
   address.
   
1. Customises the message that is sent in the invitation.

If the email address matches a person who already has a profile, then
the person is just sent an invitation; the profile is left as it was.

Send Invitations in Bulk
------------------------

Send Invitations in Bulk is complex enough to make my back teeth ache. It
reads a CSV, parsing it using `the standard Python ``csv.DictReader``
class <http://docs.python.org/library/csv.html#csv.DictReader>`_. Each
row is assumed to be a new member, with the different profile fields
in each column. There must be an email-address column, and each person
must have an email address. This address is used to check if the person
already has a profile.

* If the person already has a profile *and* is a member of the group,
  then the member is skipped.
  
* If the person already has a profile but is **not** a member of the
  group then the person is issued with an invitation.

* If the person has no profile, then one is created, the fields are set,
  and the person is issued with an invitation.

Having churned through all the rows, the page then collates the results
into four groups:

1. People who were skipped,
1. People who had existing profiles and were invited,
1. People who had a profile created and were invited,
1. Rows that had errors.

Sending invitations in bulk is nasty because of all the edge cases,
and all the parsing, and all the collation.

