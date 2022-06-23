# ,----------------------------------------------------------------------------
# code copied from pillow 8.4.0 (src/PIL/TiffImagePlugin.py)
#
# Copyright (c) 1997-2006 by Secret Labs AB.  All rights reserved.
# Copyright (c) 1995-1997 by Fredrik Lundh
# Copyright © 2010-2021 by Alex Clark and contributors
#
#
# Like PIL, Pillow is licensed under the open source HPND License:
#
# By obtaining, using, and/or copying this software and/or its associated
# documentation, you agree that you have read, understood, and will comply
# with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and its
# associated documentation for any purpose and without fee is hereby granted,
# provided that the above copyright notice appears in all copies, and that
# both that copyright notice and this permission notice appear in supporting
# documentation, and that the name of Secret Labs AB or the author not be
# used in advertising or publicity pertaining to distribution of the software
# without specific, written prior permission.
#
# SECRET LABS AB AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS
# SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS.
# IN NO EVENT SHALL SECRET LABS AB OR THE AUTHOR BE LIABLE FOR ANY SPECIAL,
# INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
# LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE
# OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.

import io
import itertools
import os

from PIL import Image, ImageOps
from PIL.ImageFile import ImageFile
# importing all symbols individually so we notice immediately when we rely
# on a newer version of pillow
from PIL.TiffImagePlugin import (logger, ImageFileDirectory_v1,
    ImageFileDirectory_v2, TiffTags,
    ARTIST, BITSPERSAMPLE, COLORMAP, COMPRESSION, COMPRESSION_INFO_REV,
    COPYRIGHT, DATE_TIME, EXTRASAMPLES, ICCPROFILE, IFDRational,
    IMAGEDESCRIPTION, IMAGELENGTH, IMAGEWIDTH, IPTC_NAA_CHUNK, JPEGQUALITY,
    PHOTOMETRIC_INTERPRETATION, PHOTOSHOP_CHUNK, PLANAR_CONFIGURATION,
    REFERENCEBLACKWHITE, RESOLUTION_UNIT, ROWSPERSTRIP, SAMPLEFORMAT,
    SAMPLESPERPIXEL, SAVE_INFO, SOFTWARE, STRIPBYTECOUNTS, STRIPOFFSETS,
    SUBIFD, TRANSFERFUNCTION, X_RESOLUTION, Y_RESOLUTION, WRITE_LIBTIFF,
    XMP)

# pillow >= 8.4.0
# upstream commit 63879f04 ("Make TIFF strip size configurable")
STRIP_SIZE = 65536
# upstream commit 5cdcc2cf ("Added tags when saving YCbCr TIFF")
YCBCRSUBSAMPLING = 530

# pillow >= 9.0.0
# upstream commit 7d4a8668 ("Block tile TIFF tags when saving")
TILEWIDTH = 322
TILELENGTH = 323
TILEBYTECOUNTS = 325


__all__ = []

def _save(im, fp, filename):

    try:
        rawmode, prefix, photo, format, bits, extra = SAVE_INFO[im.mode]
    except KeyError as e:
        raise OSError(f"cannot write mode {im.mode} as TIFF") from e

    ifd = ImageFileDirectory_v2(prefix=prefix)

    encoderinfo = im.encoderinfo
    encoderconfig = im.encoderconfig
    compression = encoderinfo.get("compression", im.info.get("compression"))
    if compression is None:
        compression = "raw"
    elif compression == "tiff_jpeg":
        # OJPEG is obsolete, so use new-style JPEG compression instead
        compression = "jpeg"
    elif compression == "tiff_deflate":
        compression = "tiff_adobe_deflate"

    libtiff = WRITE_LIBTIFF or compression != "raw"

    # required for color libtiff images
    ifd[PLANAR_CONFIGURATION] = getattr(im, "_planar_configuration", 1)

    ifd[IMAGEWIDTH] = im.size[0]
    ifd[IMAGELENGTH] = im.size[1]

    # write any arbitrary tags passed in as an ImageFileDirectory
    if "tiffinfo" in encoderinfo:
        info = encoderinfo["tiffinfo"]
    elif "exif" in encoderinfo:
        info = encoderinfo["exif"]
        if isinstance(info, bytes):
            exif = Image.Exif()
            exif.load(info)
            info = exif
    else:
        info = {}
    logger.debug("Tiffinfo Keys: %s" % list(info))
    if isinstance(info, ImageFileDirectory_v1):
        info = info.to_v2()
    for key in info:
        if isinstance(info, Image.Exif) and key in TiffTags.TAGS_V2_GROUPS.keys():
            ifd[key] = info.get_ifd(key)
        else:
            ifd[key] = info.get(key)
        try:
            ifd.tagtype[key] = info.tagtype[key]
        except Exception:
            pass  # might not be an IFD. Might not have populated type

    # additions written by Greg Couch, gregc@cgl.ucsf.edu
    # inspired by image-sig posting from Kevin Cazabon, kcazabon@home.com
    if hasattr(im, "tag_v2"):
        # preserve tags from original TIFF image file
        for key in (
            RESOLUTION_UNIT,
            X_RESOLUTION,
            Y_RESOLUTION,
            IPTC_NAA_CHUNK,
            PHOTOSHOP_CHUNK,
            XMP,
        ):
            if key in im.tag_v2:
                ifd[key] = im.tag_v2[key]
                ifd.tagtype[key] = im.tag_v2.tagtype[key]

    # preserve ICC profile (should also work when saving other formats
    # which support profiles as TIFF) -- 2008-06-06 Florian Hoech
    icc = encoderinfo.get("icc_profile", im.info.get("icc_profile"))
    if icc:
        ifd[ICCPROFILE] = icc

    for key, name in [
        (IMAGEDESCRIPTION, "description"),
        (X_RESOLUTION, "resolution"),
        (Y_RESOLUTION, "resolution"),
        (X_RESOLUTION, "x_resolution"),
        (Y_RESOLUTION, "y_resolution"),
        (RESOLUTION_UNIT, "resolution_unit"),
        (SOFTWARE, "software"),
        (DATE_TIME, "date_time"),
        (ARTIST, "artist"),
        (COPYRIGHT, "copyright"),
    ]:
        if name in encoderinfo:
            ifd[key] = encoderinfo[name]

    dpi = encoderinfo.get("dpi")
    if dpi:
        ifd[RESOLUTION_UNIT] = 2
        ifd[X_RESOLUTION] = dpi[0]
        ifd[Y_RESOLUTION] = dpi[1]

    if bits != (1,):
        ifd[BITSPERSAMPLE] = bits
        if len(bits) != 1:
            ifd[SAMPLESPERPIXEL] = len(bits)
    if extra is not None:
        ifd[EXTRASAMPLES] = extra
    if format != 1:
        ifd[SAMPLEFORMAT] = format

    if PHOTOMETRIC_INTERPRETATION not in ifd:
        ifd[PHOTOMETRIC_INTERPRETATION] = photo
    elif im.mode in ("1", "L") and ifd[PHOTOMETRIC_INTERPRETATION] == 0:
        if im.mode == "1":
            inverted_im = im.copy()
            px = inverted_im.load()
            for y in range(inverted_im.height):
                for x in range(inverted_im.width):
                    px[x, y] = 0 if px[x, y] == 255 else 255
            im = inverted_im
        else:
            im = ImageOps.invert(im)

    if im.mode in ["P", "PA"]:
        lut = im.im.getpalette("RGB", "RGB;L")
        ifd[COLORMAP] = tuple(v * 256 for v in lut)
    # data orientation
    stride = len(bits) * ((im.size[0] * bits[0] + 7) // 8)
    if ROWSPERSTRIP in info:
        rows_per_strip = info[ROWSPERSTRIP]
    elif libtiff:
        # aim for given strip size (64 KB by default) when using libtiff writer
        rows_per_strip = 1 if stride == 0 else min(STRIP_SIZE // stride, im.size[1])
        # JPEG encoder expects multiple of 8 rows
        if compression == "jpeg":
            rows_per_strip = min(((rows_per_strip + 7) // 8) * 8, im.size[1])
    else:
        rows_per_strip = im.size[1]
    if rows_per_strip == 0:
        rows_per_strip = 1
    strip_byte_counts = 1 if stride == 0 else stride * rows_per_strip
    strips_per_image = (im.size[1] + rows_per_strip - 1) // rows_per_strip
    ifd[ROWSPERSTRIP] = rows_per_strip
    if strip_byte_counts >= 2 ** 16:
        ifd.tagtype[STRIPBYTECOUNTS] = TiffTags.LONG
    ifd[STRIPBYTECOUNTS] = (strip_byte_counts,) * (strips_per_image - 1) + (
        stride * im.size[1] - strip_byte_counts * (strips_per_image - 1),
    )
    ifd[STRIPOFFSETS] = tuple(
        range(0, strip_byte_counts * strips_per_image, strip_byte_counts)
    )  # this is adjusted by IFD writer
    # no compression by default:
    ifd[COMPRESSION] = COMPRESSION_INFO_REV.get(compression, 1)

    if im.mode == "YCbCr":
        for tag, value in {
            YCBCRSUBSAMPLING: (1, 1),
            REFERENCEBLACKWHITE: (0, 255, 128, 255, 128, 255),
        }.items():
            ifd.setdefault(tag, value)

    if libtiff:
        if "quality" in encoderinfo:
            quality = encoderinfo["quality"]
            if not isinstance(quality, int) or quality < 0 or quality > 100:
                raise ValueError("Invalid quality setting")
            if compression != "jpeg":
                raise ValueError(
                    "quality setting only supported for 'jpeg' compression"
                )
            ifd[JPEGQUALITY] = quality

        logger.debug("Saving using libtiff encoder")
        logger.debug("Items: %s" % sorted(ifd.items()))
        _fp = 0
        if hasattr(fp, "fileno"):
            try:
                fp.seek(0)
                _fp = os.dup(fp.fileno())
            except io.UnsupportedOperation:
                pass

        # optional types for non core tags
        types = {}
        # SAMPLEFORMAT is determined by the image format and should not be copied
        # from legacy_ifd.
        # STRIPOFFSETS and STRIPBYTECOUNTS are added by the library
        # based on the data in the strip.
        # The other tags expect arrays with a certain length (fixed or depending on
        # BITSPERSAMPLE, etc), passing arrays with a different length will result in
        # segfaults. Block these tags until we add extra validation.
        # SUBIFD may also cause a segfault.
        blocklist = [
            REFERENCEBLACKWHITE,
            SAMPLEFORMAT,
            STRIPBYTECOUNTS,
            STRIPOFFSETS,
            TRANSFERFUNCTION,
            SUBIFD,
        ]

        atts = {}
        # bits per sample is a single short in the tiff directory, not a list.
        atts[BITSPERSAMPLE] = bits[0]
        # Merge the ones that we have with (optional) more bits from
        # the original file, e.g x,y resolution so that we can
        # save(load('')) == original file.
        legacy_ifd = {}
        if hasattr(im, "tag"):
            legacy_ifd = im.tag.to_v2()
        for tag, value in itertools.chain(
            ifd.items(), getattr(im, "tag_v2", {}).items(), legacy_ifd.items()
        ):
            # Libtiff can only process certain core items without adding
            # them to the custom dictionary.
            # Custom items are supported for int, float, unicode, string and byte
            # values. Other types and tuples require a tagtype.
            if tag not in TiffTags.LIBTIFF_CORE:
                if not Image.core.libtiff_support_custom_tags:
                    continue

                if tag in ifd.tagtype:
                    types[tag] = ifd.tagtype[tag]
                elif not (isinstance(value, (int, float, str, bytes))):
                    continue
                else:
                    type = TiffTags.lookup(tag).type
                    if type:
                        types[tag] = type
            if tag not in atts and tag not in blocklist:
                if isinstance(value, str):
                    atts[tag] = value.encode("ascii", "replace") + b"\0"
                elif isinstance(value, IFDRational):
                    atts[tag] = float(value)
                else:
                    atts[tag] = value

        logger.debug("Converted items: %s" % sorted(atts.items()))

        # libtiff always expects the bytes in native order.
        # we're storing image byte order. So, if the rawmode
        # contains I;16, we need to convert from native to image
        # byte order.
        if im.mode in ("I;16B", "I;16"):
            rawmode = "I;16N"

        # Pass tags as sorted list so that the tags are set in a fixed order.
        # This is required by libtiff for some tags. For example, the JPEGQUALITY
        # pseudo tag requires that the COMPRESS tag was already set.
        tags = list(atts.items())
        tags.sort()
        a = (rawmode, compression, _fp, filename, tags, types)
        e = Image._getencoder(im.mode, "libtiff", a, encoderconfig)
        e.setimage(im.im, (0, 0) + im.size)
        while True:
            # undone, change to self.decodermaxblock:
            l, s, d = e.encode(16 * 1024)
            if not _fp:
                fp.write(d)
            if s:
                break
        if s < 0:
            raise OSError(f"encoder error {s} when writing image file")

    else:
        offset = ifd.save(fp)

        ImageFile._save(
            im, fp, [("raw", (0, 0) + im.size, offset, (rawmode, stride, 1))]
        )

    # -- helper for multi-page save --
    if "_debug_multipage" in encoderinfo:
        # just to access o32 and o16 (using correct byte order)
        im._debug_multipage = ifd

