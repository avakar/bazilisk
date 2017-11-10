from collections import OrderedDict
import six
import xml.dom.minidom

_platforms = 'Win32', 'x64'
_configs = 'Debug', 'Release'

def _make_item(doc, name, include, *meta):
    item = doc.createElement(name)
    if include is not None:
        item.setAttribute('Include', include)

    for k, v in meta:
        m = doc.createElement(k)
        m.appendChild(doc.createTextNode(v))
        item.appendChild(m)

    return item

def _make_property_group(doc, attrs, *props):
    gr = doc.createElement('PropertyGroup')

    for k, v in attrs:
        gr.setAttribute(k, v)

    for k, v in props:
        prop = doc.createElement(k)
        prop.appendChild(doc.createTextNode(v))
        gr.appendChild(prop)
    return gr

def _make_elem(doc, tag, *attrs):
    e = doc.createElement(tag)
    for k, v in attrs:
        e.setAttribute(k, v)
    return e

def make_vcxproj(tgt, proj_map):
    fname_root, guid = proj_map[tgt]

    impl = xml.dom.minidom.getDOMImplementation()
    doc = impl.createDocument('http://schemas.microsoft.com/developer/msbuild/2003', 'Project', None)

    root = doc.documentElement
    root.setAttribute('DefaultTargets', 'Build')
    root.setAttribute('ToolsVersion', '14.0')
    root.setAttribute('xmlns', root.namespaceURI)

    conf_group = doc.createElement('ItemGroup')
    root.appendChild(conf_group)
    conf_group.setAttribute('Label', 'ProjectConfigurations')

    for plat in _platforms:
        for conf in _configs:
                conf_group.appendChild(_make_item(doc, 'ProjectConfiguration', '{}|{}'.format(conf, plat),
                ('Configuration', conf),
                ('Platform', plat),
                ))

    root.appendChild(_make_property_group(doc, [('Label', 'Globals')],
        ('ProjectGuid', '{{{}}}'.format(guid)),
        ('WindowsTargetPlaform', '8.1'),
        ))

    root.appendChild(_make_elem(doc, 'Import', ('Project', '$(VCTargetsPath)\Microsoft.Cpp.Default.props')))

    for plat in _platforms:
        for conf in _configs:
            root.appendChild(_make_property_group(doc, [('Condition', "'$(Configuration)|$(Platform)'=='{}|{}'".format(conf, plat)), ('Label', 'Configuration')],
                ('ConfigurationType', 'Application'),
                ('UseDefaultLibraries', 'true' if conf == 'Debug' else 'false'),
                ('PlatformToolset', 'v140'),
                ('CharacterSet', 'Unicode'),
                ))

    root.appendChild(_make_elem(doc, 'Import', ('Project', '$(VCTargetsPath)\Microsoft.Cpp.props')))

    root.appendChild(_make_elem(doc, 'ImportGroup', ('Label', 'ExtensionSettings')))
    root.appendChild(_make_elem(doc, 'ImportGroup', ('Label', 'Shared')))

    for plat in _platforms:
        for conf in _configs:
            e = _make_elem(doc, 'ImportGroup', ('Label', 'PropertySheets'))
            e.appendChild(_make_elem(doc, 'Import',
                ('Project', '$(UserRootDir)\Microsoft.Cpp.$(Platform).user.props'),
                ('Condition', "exists('$(UserRootDir)\Microsoft.Cpp.$(Platform).user.props')"),
                ('Label', 'LocalAppDataPlatform'),
                ))

            root.appendChild(e)

    root.appendChild(_make_elem(doc, 'PropertyGroup', ('Label', 'UserMacros')))

    for plat in _platforms:
        for conf in _configs:
            root.appendChild(_make_property_group(doc, [('Condition', "'$(Configuration)|$(Platform)'=='{}|{}'".format(conf, plat))],
                ('LinkIncremental', 'true' if conf == 'Debug' else 'false'),
                ))

    for plat in _platforms:
        conf = 'Debug'

        gr = _make_elem(doc, 'ItemDefinitionGroup', ('Condition', "'$(Configuration)|$(Platform)'=='{}|{}'".format(conf, plat)))
        gr.appendChild(_make_item(doc, 'ClCompile', None,
            ('PrecompiledHeader', ''),
            ('WarningLevel', 'Level3'),
            ('Optimization', 'Disabled'),
            ('PreprocessorDefinitions', 'WIN32;_DEBUG;_CONSOLE;%(PreprocessorDefinitions)'),
            ))

        gr.appendChild(_make_item(doc, 'Link', None,
            ('SubSystem', 'Console'),
            ('GenerateDebugInformation', 'true'),
            ))

        root.appendChild(gr)

    for plat in _platforms:
        conf = 'Release'

        gr = _make_elem(doc, 'ItemDefinitionGroup', ('Condition', "'$(Configuration)|$(Platform)'=='{}|{}'".format(conf, plat)))
        gr.appendChild(_make_item(doc, 'ClCompile', None,
            ('WarningLevel', 'Level3'),
            ('PrecompiledHeader', ''),
            ('Optimization', 'MaxSpeed'),
            ('FunctionLevelLinking', 'true'),
            ('IntrinsicFunctions', 'true'),
            ('PreprocessorDefinitions', 'WIN32;NDEBUG;_CONSOLE;%(PreprocessorDefinitions)'),
            ))

        gr.appendChild(_make_item(doc, 'Link', None,
            ('SubSystem', 'Console'),
            ('EnableCOMDATFolding', 'true'),
            ('OptimizeReferences', 'true'),
            ('GenerateDebugInformation', 'true'),
            ))

        root.appendChild(gr)

    gr = _make_elem(doc, 'ItemGroup')
    root.appendChild(gr)
    for src in tgt.srcs:
        base = src.rsplit('.', 1)
        if len(base) == 2:
            base, ext = base
        else:
            base, ext = base[0], ''
        
        if ext in ('c', 'cc', 'cxx', 'cpp'):
            type = 'ClCompile'
        elif ext in ('h', 'hh', 'hpp', 'hxx'):
            type = 'ClInclude'
        else:
            type = None

        gr.appendChild(_make_item(doc, type, src))

    gr = _make_elem(doc, 'ItemGroup')
    root.appendChild(gr)

    for dep in tgt.deps:
        fname, guid = proj_map[dep]
        root.appendChild(_make_item(doc, 'ProjectReference', fname,
            ('Project', guid),
            ))

    root.appendChild(_make_elem(doc, 'Import', ('Project', '$(VCTargetsPath)\Microsoft.Cpp.targets')))
    root.appendChild(_make_elem(doc, 'ImportGroup', ('Label', 'ExtensionTargets')))

    s = doc.toprettyxml(indent='  ', encoding='utf-8')
    return s
