SET CLIENT_ENCODING = 'UTF8';
SET CLIENT_MIN_MESSAGES = WARNING;

CREATE TABLE user_group_member_invitation (
    invitation_id        TEXT                        PRIMARY KEY,
    user_id              TEXT                        NOT NULL,
    inviting_user_id     TEXT                        NOT NULL,
    site_id              TEXT                        NOT NULL,
    group_id             TEXT                        NOT NULL,
    invitation_date      TIMESTAMP WITH TIME ZONE    NOT NULL DEFAULT NOW(),
    initial_invite       BOOL                        DEFAULT FALSE,
    response_date        TIMESTAMP WITH TIME ZONE    DEFAULT NULL,
    accepted             BOOL                        DEFAULT FALSE,
    withdrawn_date       TIMESTAMP WITH TIME ZONE    DEFAULT NULL,
    withdrawing_user_id  TIMESTAMP WITH TIME ZONE    DEFAULT NULL
);
--=mpj17=-- There is no foreign key for user_id, yet

-- INVITATION_DATE is the date the user was invited to join the group
-- INITIAL_INVITE is TRUE if it is the invitation to the *system*, rather
--    than an invitation just to a group
-- RESPONSE_DATE is the date the user responded to the invitation. If the
--    user has not responded to the invitation, it is NULL.
-- ACCEPTED is TRUE if the user accepted the invitation when he or she
--    responded; FALSE otherwise.
-- WITHDRAWN_DATE is the date the invitation was withdrawn by an 
--    administrator. If the invitation was not withdrawn it will be NULL.
-- WITHDRAWING_USER_ID is the ID of the administrator who withdrew the
--    invitation.

