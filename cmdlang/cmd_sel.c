/*
 * cmd_sel.c
 *
 * A command interpreter for OpenIPMI
 *
 * Author: MontaVista Software, Inc.
 *         Corey Minyard <minyard@mvista.com>
 *         source@mvista.com
 *
 * Copyright 2004 MontaVista Software Inc.
 *
 *  This program is free software; you can redistribute it and/or
 *  modify it under the terms of the GNU Lesser General Public License
 *  as published by the Free Software Foundation; either version 2 of
 *  the License, or (at your option) any later version.
 *
 *
 *  THIS SOFTWARE IS PROVIDED ``AS IS'' AND ANY EXPRESS OR IMPLIED
 *  WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
 *  MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
 *  IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
 *  INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
 *  BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS
 *  OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
 *  ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR
 *  TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
 *  USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 *
 *  You should have received a copy of the GNU Lesser General Public
 *  License along with this program; if not, write to the Free
 *  Software Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
 */

#include <errno.h>
#include <string.h>
#include <ctype.h>
#include <stdlib.h>
#include <stdio.h>
#include <OpenIPMI/ipmiif.h>
#include <OpenIPMI/ipmi_domain.h>
#include <OpenIPMI/ipmi_mc.h>
#include <OpenIPMI/ipmi_event.h>
#include <OpenIPMI/ipmi_cmdlang.h>
#include <OpenIPMI/ipmi_int.h>

static void
sel_list(ipmi_domain_t *domain, void *cb_data)
{
    ipmi_cmd_info_t *cmd_info = cb_data;
    char            domain_name[IPMI_MAX_DOMAIN_NAME_LEN];
    int             rv;
    unsigned int    count1, count2;
    ipmi_event_t    *event, *event2;

    ipmi_domain_get_name(domain, domain_name, sizeof(domain_name));

    ipmi_cmdlang_out(cmd_info, "Domain", NULL);
    ipmi_cmdlang_down(cmd_info);
    ipmi_cmdlang_out(cmd_info, "Name", domain_name);
    rv = ipmi_domain_sel_count(domain, &count1);
    if (rv)
	return;
    rv = ipmi_domain_sel_entries_used(domain, &count2);
    if (rv)
	return;
    ipmi_cmdlang_out_int(cmd_info, "Entries", count1);
    ipmi_cmdlang_out_int(cmd_info, "Slots in use", count2);

    event = ipmi_domain_first_event(domain);
    while (event) {
	ipmi_cmdlang_out(cmd_info, "Event", NULL);
	ipmi_cmdlang_down(cmd_info);
	ipmi_cmdlang_event_out(event, cmd_info);
	ipmi_cmdlang_up(cmd_info);
	event2 = ipmi_domain_next_event(domain, event);
	ipmi_event_free(event);
	event = event2;
    }
    ipmi_cmdlang_up(cmd_info);
}

typedef struct sel_delete_s
{
    ipmi_cmd_info_t *cmd_info;
    int             record;
    char            mc_name[IPMI_MC_NAME_LEN];
} sel_delete_t;

static void
sel_delete_done(ipmi_domain_t *domain, int err, void *cb_data)
{
    sel_delete_t    *info = cb_data;
    ipmi_cmd_info_t *cmd_info = info->cmd_info;
    ipmi_cmdlang_t  *cmdlang = ipmi_cmdinfo_get_cmdlang(cmd_info);

    ipmi_cmdlang_lock(cmd_info);
    if (err) {
	cmdlang->errstr = "Error deleting SEL entry";
	cmdlang->err = err;
	ipmi_domain_get_name(domain, cmdlang->objstr,
			     cmdlang->objstr_len);
	cmdlang->location = "cmd_sel.c(sel_delete_done)";
	goto out;
    }

    ipmi_cmdlang_out(cmd_info, "Event deleted", NULL);
    ipmi_cmdlang_down(cmd_info);
    ipmi_cmdlang_out(cmd_info, "MC", info->mc_name);
    ipmi_cmdlang_out_int(cmd_info, "Record", info->record);
    ipmi_cmdlang_up(cmd_info);

 out:
    ipmi_mem_free(info);
    ipmi_cmdlang_unlock(cmd_info);
    ipmi_cmdlang_cmd_info_put(cmd_info);
}

static void
sel_delete(ipmi_mc_t *mc, void *cb_data)
{
    ipmi_cmd_info_t *cmd_info = cb_data;
    ipmi_cmdlang_t  *cmdlang = ipmi_cmdinfo_get_cmdlang(cmd_info);
    int             rv;
    int             curr_arg = ipmi_cmdlang_get_curr_arg(cmd_info);
    int             argc = ipmi_cmdlang_get_argc(cmd_info);
    char            **argv = ipmi_cmdlang_get_argv(cmd_info);
    ipmi_event_t    *event = NULL;
    int             record_id;
    sel_delete_t    *info;

    if ((argc - curr_arg) < 1) {
	cmdlang->errstr = "Not enough parameters";
	cmdlang->err = EINVAL;
	goto out_err;
    }

    ipmi_cmdlang_get_int(argv[curr_arg], &record_id, cmd_info);
    if (cmdlang->err) {
	cmdlang->errstr = "Record id invalid";
	goto out_err;
    }
    curr_arg++;

    event = ipmi_mc_event_by_recid(mc, record_id);
    if (!event) {
	cmdlang->errstr = "Event not found";
	cmdlang->err = EINVAL;
	goto out_err;
    }

    info = ipmi_mem_alloc(sizeof(*info));
    if (!info) {
	cmdlang->errstr = "Out of memory";
	cmdlang->err = ENOMEM;
	goto out_err;
    }
    info->cmd_info = cmd_info;
    info->record = record_id;
    ipmi_mc_get_name(mc, info->mc_name, sizeof(info->mc_name));

    ipmi_cmdlang_cmd_info_get(cmd_info);
    rv = ipmi_event_delete(event, sel_delete_done, info);
    if (rv) {
	ipmi_cmdlang_cmd_info_put(cmd_info);
	cmdlang->errstr = "Error deleting event";
	cmdlang->err = rv;
	ipmi_mem_free(info);
	goto out_err;
    }
    ipmi_event_free(event);
    return;

 out_err:
    ipmi_mc_get_name(mc, cmdlang->objstr,
		     cmdlang->objstr_len);
    cmdlang->location = "cmd_sel.c(sel_delete)";
    if (event)
	ipmi_event_free(event);
}

static void
sel_add_done(ipmi_mc_t    *mc,
	     unsigned int record_id,
	     int          err,
	     void         *cb_data)
{
    ipmi_cmd_info_t *cmd_info = cb_data;
    ipmi_cmdlang_t  *cmdlang = ipmi_cmdinfo_get_cmdlang(cmd_info);

    ipmi_cmdlang_lock(cmd_info);
    if (err) {
	cmdlang->errstr = "Error adding SEL entry";
	cmdlang->err = err;
	ipmi_mc_get_name(mc, cmdlang->objstr,
			 cmdlang->objstr_len);
	cmdlang->location = "cmd_sel.c(sel_add_done)";
    } else {
	char mc_name[IPMI_MC_NAME_LEN];

	ipmi_mc_get_name(mc, mc_name, sizeof(mc_name));
	ipmi_cmdlang_out(cmd_info, "MC", NULL);
	ipmi_cmdlang_down(cmd_info);
	ipmi_cmdlang_out(cmd_info, "Name", mc_name);
	ipmi_cmdlang_out_int(cmd_info, "Record ID", record_id);
	ipmi_cmdlang_up(cmd_info);
    }
    ipmi_cmdlang_unlock(cmd_info);
    ipmi_cmdlang_cmd_info_put(cmd_info);
}

static void
sel_add(ipmi_mc_t *mc, void *cb_data)
{
    ipmi_cmd_info_t *cmd_info = cb_data;
    ipmi_cmdlang_t  *cmdlang = ipmi_cmdinfo_get_cmdlang(cmd_info);
    int             rv;
    int             curr_arg = ipmi_cmdlang_get_curr_arg(cmd_info);
    int             argc = ipmi_cmdlang_get_argc(cmd_info);
    char            **argv = ipmi_cmdlang_get_argv(cmd_info);
    ipmi_event_t    *event = NULL;
    int             type;
    unsigned char   data[13];
    int             i;

    if ((argc - curr_arg) < 14) {
	cmdlang->errstr = "Not enough parameters";
	cmdlang->err = EINVAL;
	goto out_err;
    }

    ipmi_cmdlang_get_int(argv[curr_arg], &type, cmd_info);
    if (cmdlang->err) {
	cmdlang->errstr = "Record type invalid";
	goto out_err;
    }
    curr_arg++;

    i = 0;
    while (curr_arg < argc) {
	ipmi_cmdlang_get_uchar(argv[curr_arg], &data[i], cmd_info);
	if (cmdlang->err) {
	    cmdlang->errstr = "data invalid";
	    goto out_err;
	}
	curr_arg++;
	i++;
    }

    event = ipmi_event_alloc(ipmi_mc_convert_to_id(mc),
			     0, type, 0, data, 13);
    if (!event) {
	cmdlang->errstr = "Out of memory";
	cmdlang->err = ENOMEM;
	goto out_err;
    }

    ipmi_cmdlang_cmd_info_get(cmd_info);
    rv = ipmi_mc_add_event_to_sel(mc, event, sel_add_done, cmd_info);
    if (rv) {
	ipmi_cmdlang_cmd_info_put(cmd_info);
	cmdlang->errstr = "Error adding event";
	cmdlang->err = rv;
	goto out_err;
    }
    ipmi_event_free(event);
    return;

 out_err:
    ipmi_mc_get_name(mc, cmdlang->objstr,
		     cmdlang->objstr_len);
    cmdlang->location = "cmd_sel.c(sel_add)";
    if (event)
	ipmi_event_free(event);
}

static void
sel_clear(ipmi_domain_t *domain, void *cb_data)
{
    ipmi_cmd_info_t *cmd_info = cb_data;
    ipmi_event_t    *event, *event2;
    char            domain_name[IPMI_MAX_DOMAIN_NAME_LEN];

    ipmi_domain_get_name(domain, domain_name, sizeof(domain_name));

    event = ipmi_domain_first_event(domain);
    while (event) {
	event2 = event;
	event = ipmi_domain_next_event(domain, event2);
	ipmi_domain_del_event(domain, event2, NULL, NULL);
	ipmi_event_free(event2);
    }
    ipmi_cmdlang_out(cmd_info, "SEL Clear done", domain_name);
}

static ipmi_cmdlang_cmd_t *sel_cmds;

static ipmi_cmdlang_init_t cmds_sel[] =
{
    { "sel", NULL,
      "- Commands dealing with the SEL",
      NULL, NULL, &sel_cmds},
    { "list", &sel_cmds,
      "<domain> - List all the events in the domain",
      ipmi_cmdlang_domain_handler, sel_list, NULL },
    { "delete", &sel_cmds,
      "<mc> <record id> - Delete the given event.",
      ipmi_cmdlang_mc_handler, sel_delete, NULL },
    { "add", &sel_cmds,
      "<mc> <record type> <13 data bytes> - add the given event to the"
      " MC's sel.",
      ipmi_cmdlang_mc_handler, sel_add, NULL },
    { "clear", &sel_cmds,
      "<domain> - Delete all events in the domain.",
      ipmi_cmdlang_domain_handler, sel_clear, NULL },
};
#define CMDS_SEL_LEN (sizeof(cmds_sel)/sizeof(ipmi_cmdlang_init_t))

int
ipmi_cmdlang_sel_init(void)
{
    return ipmi_cmdlang_reg_table(cmds_sel, CMDS_SEL_LEN);
}
