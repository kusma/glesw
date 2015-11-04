#!/bin/env python
import sys
import argparse
import xml.etree.ElementTree

def format_params(command):
    params = command.findall("param");
    param_strings = []
    for param in params:
        param_strings.append("".join(param.itertext()))
    return ", ".join(param_strings)

def get_typename(name):
    return "PFN" + name.upper() + "PROC"

def format_typedef(command):
    proto = command.find("proto");

    # returntype = "".join(proto.itertext()) # BUG: this includes the name
    returntype = proto.text or ""
    ptype = proto.find('ptype')
    if ptype != None:
        returntype += ptype.text or ""

    apientry = "GL_APIENTRY"
    typename = get_typename(proto.find('name').text)
    params = format_params(command);
    return "typedef " + returntype + " (" + apientry + " * " + typename + ")(" + params + ");"

def find_command(root, name):
    commands = root.find("commands")
    for command in commands:
        if name == command.find("proto").find("name").text:
            return command
    raise Exception("could not find command: " + name)

def find_enum(root, name):
    enumgroups = root.findall("enums")
    for enumgroup in enumgroups:
        enums = enumgroup.findall("enum")
        for enum in enums:
            if enum.attrib['name'] == name and enum.attrib['value'] != None:
                return enum
    raise Exception("could not find enum: " + name)

def emit_command_typedef(root, name):
    return format_typedef(find_command(root, name))

def emit_enum_define(root, name):
    enum = find_enum(root, name)
    return "#define " + name + " " + enum.attrib['value']

def emit_command_loader(root, name):
    return format_loader(find_command(root, name))

commands = {}

def emit_extension(root, api, extension, defs, members, body):
    name = extension.attrib['name']

    members.append("/* " + name + " */");
    members.append("bool have_" + name + ";")

    requires = extension.findall("require")
    if requires != None:
        defs.append("#ifndef " + name)
        defs.append("#define " + name + " 1")
        defs.append("")

        for require in requires:
            if require.attrib.has_key('api') and require.attrib['api'] != api:
                continue

            for child in require:
                if child.tag == "command":
                    cmdname = child.attrib['name']
                    if commands.has_key(cmdname) == False:
                        defs.append(emit_command_typedef(root, cmdname))
                        typename = get_typename(cmdname)
                        funcname = "func_" + cmdname
                        members.append(typename + " " + funcname + ";")
                        commands[cmdname] = True
                elif child.tag == "enum":
                    defs.append(emit_enum_define(root, child.attrib['name']))

        defs.append("")
        defs.append("#endif /* " + name +" */\n")

    members.append("")

def emit_api_extensions(fp, root, api):

    # TODO: we don't generate some dependent typedefs properly, so get
    # them from the normal GLES headers for now.

    fp.write("#include <GLES2/gl2.h>\n\n");

    defs = []
    members = []
    body = []
    extensions = root.find("extensions")
    for extension in extensions:
        name = extension.attrib['name']
        supported = extension.attrib['supported'].split('|')
        if api in supported:
           emit_extension(root, api, extension, defs, members, body)

    fp.write("\n".join(defs) + "\n")

    print "struct extensions\n{\n"
    for member in members:
        print "\t" + member
    print "};\n"

    for line in body:
        print line


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate OpenGL bindings from XML.")
    parser.add_argument('infile', nargs='?', type=argparse.FileType('r'),
                        default=sys.stdin)
    parser.add_argument('outfile', nargs='?', type=argparse.FileType('w'),
                        default=sys.stdout)
    args = parser.parse_args();

    tree = xml.etree.ElementTree.parse(args.infile)
    root = tree.getroot()
    emit_api_extensions(sys.stdout, root, 'gles2')
