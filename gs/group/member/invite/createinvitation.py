# coding=utf-8
from email.Message import Message
from email.Header import Header
from email.MIMEText import MIMEText
from email.MIMEMultipart import MIMEMultipart

utf8 = 'utf-8'
def create_invitation_message(fromAddr, toAddr, supportAddr, subject, message, inviteId, contentProvider):
    '''Construct the MIME message that contains the invitation.
    
    ARGUMENTS
    ---------
    
    ``fromAddr``
        The Addressee from which the message is sent.
        
    ``toAddr``
        The Addressee to which the message is sent.
        
    ``supportAddr``
        The Addressee for the support-address of the site.
        
    ``subject``
        The subject of the invitation (Unicode)
        
    ``message``
        The message (Unicode).
        
    ``contentProvider``
        The content provider used to format the message
        
    RETURNS
    -------
    
    A string (str) containing the entire message, MIME-encoded in both 
    ``text/plain`` and ``text/html`` formats.
    
    SIDE EFFECTS
    ------------
    
    None.'''
    
    container = MIMEMultipart('alternative')
    container['Subject'] = str(Header(subject, utf8))
    container['From'] = str(fromAddr)
    container['To'] = str(toAddr)
    container['Reply-to'] = str(supportAddr)
    
    contentProvider.preview = False
    contentProvider.body = message
    contentProvider.invitationId = inviteId

    contentProvider.text = True
    contentProvider.update()
    t = contentProvider.render()
    text = MIMEText(t.strip().encode(utf8), 'plain', utf8)
    container.attach(text)
    
    contentProvider.text = False
    contentProvider.body = message.strip().replace('\n', '<br/>')
    h = contentProvider.render()
    html = MIMEText(h.encode(utf8), 'html', utf8)    
    container.attach(html)
    
    retval = container.as_string()
    assert retval
    assert type(retval) == str
    return retval

