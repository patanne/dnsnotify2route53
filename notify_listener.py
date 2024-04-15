import datetime
import logging
import globals

import socket

import dns.flags
import dns.message
import dns.rdataclass
import dns.rdatatype
import dns.name

from typing import cast


def listen_for_notify():
    address = globals.config.listen_ip
    port    = globals.config.listen_port

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((address, port))
    message = f"listener created at {datetime.datetime.now().strftime(globals.timestamp_format)}."
    logging.info(message)
    while True:
        (wire, address) = s.recvfrom(512)
        notify = dns.message.from_wire(wire)

        error_happened = True
        try:
            soa = notify.find_rrset(notify.answer, notify.question[0].name, dns.rdataclass.IN, dns.rdatatype.SOA)

            # Do something with the SOA RR here
            error_happened = False
        except KeyError:
            # No SOA RR in the answer section.
            pass

        server_ip = address[0]
        domain_name  = soa.name.to_text(True)
        serial = soa[0].serial
        message = f"notify received at {datetime.datetime.now().strftime(globals.timestamp_format)} local time from server {server_ip} for domain {domain_name} with serial number {serial}."
        print(message)
        logging.info(message)

        response = dns.message.make_response(notify)  # type: dns.message.Message
        response.flags |= dns.flags.AA
        wire = response.to_wire(cast(dns.name.Name, response))
        s.sendto(wire, address)

        if error_happened: continue
        if server_ip in globals.config.notify_servers:
            # we are listening to this server
            if domain_name in globals.config.domains_to_manage:
                # we are listening for this domain
                globals.wq.put((domain_name,serial))


