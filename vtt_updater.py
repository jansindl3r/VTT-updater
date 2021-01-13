import re
import xml.etree.ElementTree as et

from fontTools.ttLib.ttFont import TTFont
from fontTools.pens.recordingPen import RecordingPen
from pathlib import Path
from itertools import zip_longest
from typing import Union


__all__ = ["VTT_XML_legacy_updater", "VTT_updater"]


class VTT_XML_legacy_updater:
    def __init__(
        self,
        path_old: Union[Path, str],
        path_new: Union[Path, str],
        path_xml: Union[Path, str],
    ):
        self.font_old = TTFont(str(path_old))
        self.font_new = TTFont(str(path_new))
        self.tree = et.parse(str(path_xml))

    def update(self):
        glyphs_dict = {}
        font = TTFont(font_VTT_source)
        glyphs = font.getGlyphOrder()
        for glyph in glyphs:
            glyphs_dict[glyph] = [font.getGlyphID(glyph)]

        font = TTFont(font_new)
        glyphs = font.getGlyphOrder()
        for glyph in glyphs:
            if glyph in glyphs_dict:
                glyphs_dict[glyph].append(font.getGlyphID(glyph))

        id_dict = {v[0]: v[1] for v in glyphs_dict.values() if len(v) == 2}

        root = self.tree.find("glyf")

        for child in root:
            talk = child.find("instructions//talk").text
            if talk != None:
                glyph_id = child.attrib["ID"]
                new_id = id_dict[int(glyph_id)]
                child.set("ID", str(id_dict[int(glyph_id)]))
            assembly = child.find("instructions//assembly").text
            assembly_content = []
            if assembly:
                for line in assembly.split("\n"):
                    if line.startswith("OFFSET[R]"):
                        line = line.split(",")
                        line[1] = " %s" % (id_dict[int(line[1])])
                        line = ",".join(line)
                        print(line)
                    assembly_content.append(line)
                child.find("instructions//assembly").text = "\n".join(assembly_content)

    def write(self, save_as: Union[Path, str]):
        self.tree.write(str(save_as))


class VTT_updater:
    def __init__(
        self, path_old: Union[Path, str], path_new: Union[Path, str], log: bool = True
    ) -> None:

        self.font_old = TTFont(str(path_old))
        self.font_old.cmap = {v: k for k, v in self.path_old.getBestCmap().items()}
        self.font_old.go = self.path_old.getGlyphOrder()
        self.font_old.path = path_old

        self.font_new = TTFont(str(path_new))
        self.font_new.cmap = self.path_new.getBestCmap()
        self.font_new.go = self.path_new.getGlyphOrder()
        self.font_new.path = path_new

        self.log = True

        self.name_map = {
            k: self.font_new.cmap.get(v) for k, v in self.font_old.cmap.items()
        }
        self.name_map.update(
            {i: i for i in filter(lambda x: x in self.font_new.go, self.font_old.go)}
        )
        self.incompatible_glyphs = self.get_incompatible_glyphs()

    def get_glyph_map(self) -> dict:
        glyph_map = {}
        for i, g_new in enumerate(self.font_new.go):
            if g_new in self.font_old.go:
                glyph_map[self.font_old.index(g_new)] = i
            return glyph_map

    def get_incompatible_glyphs(self) -> list:
        incompatible_glyphs = list(
            filter(lambda x: not self.name_map[x] in self.font_new.go, self.font_old.go)
        )
        for g_name in self.font_old.go:
            if g_name not in incompatible_glyphs:
                g_old = self.font_old["glyf"][g_name]
                g_new = self.font_new["glyf"][self.name_map[g_name]]

                pen_old = RecordingPen()
                g_old.draw(pen_old, self.font_old["glyf"])

                pen_new = RecordingPen()
                g_new.draw(pen_new, self.font_new["glyf"])

                for (pt_old, *_), (pt_new, *_) in zip_longest(
                    pen_old.value, pen_new.value, fillvalue=[None, None]
                ):
                    if pt_old != pt_new:
                        if self.log:
                            print(
                                f"{g_name}/{self.name_map[g_name]} has an incompatible contour"
                            )
                        break
                else:
                    if hasattr(g_old, "components") and hasattr(g_new, "components"):
                        for comp_old, comp_new in zip_longest(
                            g_old.components, g_new.components
                        ):
                            if comp_old.glyphName != comp_new.glyphName:
                                if self.log:
                                    print(
                                        f"{g_name}/{self.name_map[g_name]} has incompatible components"
                                    )
                                break
                    continue
                incompatible_glyphs.append(g_name)
        return incompatible_glyphs

    def update_assembly(self) -> None:
        for g_name in self.font_old.go:
            if g_name not in self.incompatible_glyphs:
                g_old = self.font_old["glyf"][g_name]
                if hasattr(g_old, "program"):
                    g_new = self.font_new["glyf"][self.name_map[g_name]]
                    g_new.program = g_old.program
        return None

    def update_glyph_programs(self, font) -> None:
        pattern = r"(.*OFFSET\[[r,R]\]\ ?),.*"
        for key in font["TSI1"].glyphPrograms:
            glyph_program = font["TSI1"].glyphPrograms[key].replace("\r", "\n")
            matches = list(re.finditer(pattern, glyph_program))
            if matches:
                components = self.font_new["glyf"][self.name_map[key]].components
                for match, component in zip(matches[::-1], components[::-1]):
                    left, right = match.span(0)
                    command = match.group(1)
                    g_name, (*transformations, x, y) = component.getComponentInfo()
                    assembly = [x, y]
                    if transformations != [1, 0, 0, 1]:
                        assembly.extend(transformations)
                    assembly = list(map(str, assembly))
                    gid = self.font_new.go.index(g_name)
                    new_command = f"{command}, {gid}, {', '.join(assembly)}"
                    glyph_program = (
                        glyph_program[:left] + new_command + glyph_program[right:]
                    )
                font["TSI1"].glyphPrograms[key] = glyph_program.replace("\n", "\r")
        return None

    def _filter_glyphs(self, dict_data) -> dict:
        new_dict_data = {}
        keys = [i for i in dict_data.keys()]
        for key in keys:
            if key not in self.incompatible_glyphs:
                new_dict_data[self.name_map[key]] = dict_data[key]
        return new_dict_data

    def update_TSI_tables(self) -> None:

        self.font_new["TSI0"] = self.font_old["TSI0"]  # empty...
        self.font_new["TSI1"] = self.font_old["TSI1"]  # assembly
        self.font_new["TSI2"] = self.font_old["TSI2"]  # empty...
        self.font_new["TSI3"] = self.font_old["TSI3"]  # VTT talks
        self.font_new["TSI5"] = self.font_old["TSI5"]  # glyph groups
        self.font_new["cvt "] = self.font_old["cvt "]  # cvts
        self.font_new["prep"] = self.font_old["prep"]  # prep
        self.font_new["fpgm"] = self.font_old["fpgm"]  # fpgm

        self.font_new["TSI1"].glyphPrograms = self._filter_glyphs(
            self.font_new["TSI1"].glyphPrograms
        )
        self.font_new["TSI3"].glyphPrograms = self._filter_glyphs(
            self.font_new["TSI3"].glyphPrograms
        )
        return None

    def update_table_entries(self) -> None:
        update = dict(
            maxp=[
                "maxSizeOfInstructions",
                "maxFunctionDefs",
                "maxStorage",
                "maxStackElements",
                "maxZones",
                "maxTwilightPoints",
            ],
            head=["checkSumAdjustment"],
        )

        for table, attributes in update.items():
            for attribute in attributes:
                setattr(
                    self.font_new[table],
                    attribute,
                    getattr(self.font_old[table], attribute),
                )

        self.font_new["head"].flags |= 1 << 3

        return None

    def update(self) -> None:
        self.update_assembly()
        self.update_glyph_programs(self.font_old)
        self.update_TSI_tables()
        self.update_table_entries()
        return None

    def write(self, save_as: Union[Path, str, bool] = None) -> None:
        if save_as:
            self.font_new.save(str(save_as))
        else:
            self.font_new.save(str(self.font_new.path))
        return None


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser(
        description="""\

###########################
### |####/ __  _____  __/##
### |##/ /##/ /####/ /#####
###  / /###/ /####/ /######
###__/####/_/####/_/#######
###########################
VTT file updater                        

    Jan Šindler, jansindl3r@gmail.com

        Update VTT old file to a new one. It updates glyph order, transfers 
        compatible instructions and gives a warning if something is not compatible
        """,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "font_old", type=Path, 
        help="""\
A path to old file containing VTT data
        """
    )
    parser.add_argument(
        "font_new",
        type=Path,
        help="""\
A path to a TTF in which you want to import the VTT data
        """,
    )
    parser.add_argument(
        "-s",
        "--save_as",
        help="""\
A path where you want to output the updated file. 
Not setting it rewrites the. Don't set if you want your new font to be rewritten.
        """,
    )
    parser.add_argument(
        "--log",
        type=bool,
        nargs="?",
        const=True,
        default=False,
        help="""\
Log or not to log, that's the question!
        """,
    )
    parser.add_argument(
        "--legacy",
        type=bool,
        nargs="?",
        const=True,
        default=False,
        help="""\
Use legacy mode instead. This requires extra step of providing additional 
XML file exported in VTT. You find it in VTT, File > Export > All code to XML... 
        """,
    )

    args = parser.parse_args()
    print(args)
    xxxx
    if not args.legacy:
        project = VTT_updater(args.font_old, args.font_new, log=args.log)
    else:
        project = VTT_XML_legacy_updater(args.font_old, args.font_new)

    project.update()
    project.save(args.save_as)
