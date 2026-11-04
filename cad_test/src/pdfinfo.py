import pymupdf, collections
doc = pymupdf.open('show.pdf')
print("pages:", doc.page_count, "| metadata:", {k: v for k, v in doc.metadata.items() if v})
ocgs = doc.get_ocgs()
print("PDF layers (OCGs):", len(ocgs))
for xref, o in list(ocgs.items())[:80]: print("   ", o.get('name'), '| on' if o.get('on') else '| off')
for i, page in enumerate(doc):
    w, h = page.rect.width * 25.4 / 72, page.rect.height * 25.4 / 72
    imgs = page.get_images(full=True)
    txt = page.get_text('text')
    words = page.get_text('words')
    print(f"\n--- page {i+1}: {round(w)} x {round(h)} mm, rotation {page.rotation}")
    print(f"    images: {len(imgs)}", [(im[2], im[3]) for im in imgs[:6]])
    try:
        dr = page.get_drawings()
        print(f"    vector paths: {len(dr)}")
    except Exception as ex:
        print("    vector paths: error", ex)
    print(f"    text words: {len(words)} | sample: {txt[:300]!r}")
