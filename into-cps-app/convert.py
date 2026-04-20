
import xml.etree.ElementTree as ET

def convert(in_path, out_path):
    tree = ET.parse(in_path)
    root = tree.getroot()

    model_variables_node = root.find('.//ModelVariables')
    for elem in root.findall('.//ModelVariables/'):
        comment = ET.Comment(f"{elem.tag}, {elem.attrib}")
        idx = list(model_variables_node).index(elem)
        model_variables_node.insert(idx, comment)
        match  elem.tag:
            case 'Float64'| 'Float32':
                type_name = 'Real'
            case 'Int64'| 'Int32'|'UInt32':
                type_name = 'Integer'
            case 'String':
                type_name = 'String'
            case 'Boolean':
                type_name = 'Boolean'
            case 'Clock':
                type_name = 'Integer'
            case 'ScalarVariable':
                continue
            case _:
                print(f"Unknown type {elem.tag}")
                type_name = 'Unknown'

        type_node = ET.Element(type_name)
        if 'start' in elem.attrib:
            type_node.attrib['value'] = elem.attrib['start']
            elem.attrib.pop('start')
        elem.append(type_node)


        elem.tag ='ScalarVariable'


    tree.write(out_path, encoding="utf-8", xml_declaration=True)



from pathlib import Path
import glob

search_root = Path(__file__).parent.parent

def map_binary(binaries_ource:Path,binaries:Path,source,target):
    darwin64 =  binaries/target
    darwin64.mkdir(parents=True,exist_ok=True)
    dylibs = list((binaries_ource/source).glob("*.dylib"))+list((binaries_ource/source).glob("*.dll"))+list((binaries_ource/source).glob("*.so")) 
    if len(dylibs) == 1:
        dylib = dylibs[0]
        if not (darwin64/dylib.name).exists():
            (darwin64/dylib.name).symlink_to(dylib)
            
libs={
    'x86_64-darwin' : 'darwin64',
    'x86_64-linux' : 'linux64',
    'x86_64-windows' : 'win64',
}

for file in glob.glob(str(search_root/'**'/'modelDescription.xml'),recursive=True):
    if 'info-cps-app' in file or 'original_FMUs' in file:
        continue
    target_path = Path(__file__).parent/'FMUs' /Path(file).relative_to(search_root)
    target_path.parent.mkdir(parents=True,exist_ok=True)
    binaries = target_path.parent/'binaries'
    
    for source, target in libs.items():
        map_binary(Path(file).parent/'binaries',binaries,source,target)
    
    print(f"Converting {file} to {target_path}")
    convert(file,target_path)