/**
 * boostly_ae_pro.jsx
 * ==================
 * סקריפט After Effects מקצועי לסרטון שיווקי Boostly
 * עברית RTL אמיתית | עיצוב נקי | מיקומים מחושבים
 *
 * הרצה: File > Scripts > Run Script File > boostly_ae_pro.jsx
 */
(function () {
    app.beginUndoGroup("Boostly Pro");
    try {

    // ── הגדרות ──────────────────────────────────────
    var W   = 1080;
    var H   = 1920;
    var FPS = 30;
    var DUR = 27; // שניות

    var proj = app.project;
    var comp = proj.items.addComp("Boostly_Pro", W, H, 1, DUR, FPS);
    comp.bgColor = [0.04, 0.01, 0.09];

    // ── צבעים (0-1) ──────────────────────────────────
    var WHITE  = [1.00, 1.00, 1.00];
    var PURPLE = [0.49, 0.23, 0.93];
    var PINK   = [0.93, 0.28, 0.60];
    var ORANGE = [0.98, 0.45, 0.06];
    var GOLD   = [0.98, 0.82, 0.12];
    var GREEN  = [0.16, 0.90, 0.50];
    var LGRAY  = [0.70, 0.65, 0.88];
    var DARK   = [0.06, 0.02, 0.14];
    var DPURP  = [0.10, 0.03, 0.22];

    // ── helpers ────────────────────────────────────────
    function f(sec)   { return sec * FPS; }
    function ft(sec)  { return sec; }        // inPoint/outPoint = שניות

    function ease2(prop) {
        try {
            var e = new KeyframeEase(0, 66);
            for (var i = 1; i <= prop.numKeys; i++)
                prop.setTemporalEaseAtKey(i, [e], [e]);
        } catch (x) {}
    }

    /* ── addText: טקסט עברי RTL מלא ── */
    function addText(str, size, color, cx, cy, inSec, outSec, justify) {
        var L = comp.layers.addText(str);
        L.inPoint  = ft(inSec);
        L.outPoint = ft(outSec);

        try {
            var sp = null;
            try { sp = L.property("ADBE Text Properties").property("ADBE Text Document"); } catch(e){}
            if (!sp) { try { sp = L.property("Text").property("Source Text"); } catch(e){} }

            if (sp) {
                var d = sp.value;
                try { d.fontSize  = size; }          catch(e){}
                try { d.fillColor = color; }         catch(e){}
                try { d.applyFill = true; }          catch(e){}
                try { d.font = "Arial-BoldMT"; }     catch(e){}
                // RTL
                try { d.baselineDirection = 2; }     catch(e){}   // RIGHT_TO_LEFT
                try { d.fauxBold = false; }          catch(e){}

                // יישור: ברירת מחדל = מרכז
                var j = justify || ParagraphJustification.CENTER_JUSTIFY;
                try { d.justification = j; }         catch(e){}

                sp.setValue(d);
            }
        } catch(te){}

        // מרכז לפי מיקום
        try {
            L.property("Position").setValue([cx, cy]);
            L.property("Anchor Point").setValue([0, 0]);
        } catch(e){}

        return L;
    }

    /* ── אנימציות ── */
    function fadeIn(L, startSec, durFrames) {
        durFrames = durFrames || 15;
        try {
            var op = L.property("Opacity");
            op.setValueAtTime(ft(startSec),                  0);
            op.setValueAtTime(ft(startSec + durFrames/FPS), 100);
            ease2(op);
        } catch(e){}
    }

    function fadeOut(L, startSec, durFrames) {
        durFrames = durFrames || 12;
        try {
            var op = L.property("Opacity");
            op.setValueAtTime(ft(startSec),                  100);
            op.setValueAtTime(ft(startSec + durFrames/FPS),  0);
            ease2(op);
        } catch(e){}
    }

    function slideUp(L, startSec, dist) {
        dist = dist || 60;
        try {
            var pos = L.property("Position");
            var v   = pos.value;
            pos.setValueAtTime(ft(startSec),            [v[0], v[1] + dist]);
            pos.setValueAtTime(ft(startSec + 20/FPS),   [v[0], v[1]]);
            ease2(pos);
        } catch(e){}
    }

    function scalePop(L, startSec) {
        try {
            var sc = L.property("Scale");
            sc.setValueAtTime(ft(startSec),            [0,   0,   100]);
            sc.setValueAtTime(ft(startSec + 14/FPS),   [112, 112, 100]);
            sc.setValueAtTime(ft(startSec + 24/FPS),   [100, 100, 100]);
            ease2(sc);
        } catch(e){}
    }

    /* ── shape rect ── */
    function addRect(cx, cy, w, h, color, inSec, outSec, rx) {
        var L = comp.layers.addShape();
        L.inPoint  = ft(inSec);
        L.outPoint = ft(outSec);
        try {
            var grp  = L.property("ADBE Root Vectors Group").addProperty("ADBE Vector Group");
            var cont = grp.property("ADBE Vectors Group");
            var rect = cont.addProperty("ADBE Vector Shape - Rect");
            rect.property("ADBE Vector Rect Size").setValue([w, h]);
            rect.property("ADBE Vector Rect Roundness").setValue(rx || 0);
            var fill = cont.addProperty("ADBE Vector Graphic - Fill");
            fill.property("ADBE Vector Fill Color").setValue(color);
        } catch(e){}
        try { L.property("Position").setValue([cx, cy]); } catch(e){}
        return L;
    }

    /* ── shape circle ── */
    function addCircle(cx, cy, r, color, inSec, outSec) {
        var L = comp.layers.addShape();
        L.inPoint  = ft(inSec);
        L.outPoint = ft(outSec);
        try {
            var grp  = L.property("ADBE Root Vectors Group").addProperty("ADBE Vector Group");
            var cont = grp.property("ADBE Vectors Group");
            var ell  = cont.addProperty("ADBE Vector Shape - Ellipse");
            ell.property("ADBE Vector Ellipse Size").setValue([r*2, r*2]);
            var fill = cont.addProperty("ADBE Vector Graphic - Fill");
            fill.property("ADBE Vector Fill Color").setValue(color);
        } catch(e){}
        try { L.property("Position").setValue([cx, cy]); } catch(e){}
        return L;
    }

    /* ── קו מפריד ── */
    function addLine(cy, inSec, outSec) {
        return addRect(W/2, cy, 700, 3, PURPLE, inSec, outSec, 2);
    }

    // ════════════════════════════════════════════════════
    //  SCENE 1 — לוגו ומיתוג  (0-5 שניות)
    // ════════════════════════════════════════════════════
    // רקע נוסף: עיגול זוהר מאחורי הלוגו
    var glowBg = addCircle(W/2, 720, 280, [0.20, 0.05, 0.38], 0, DUR);
    try { glowBg.property("Opacity").setValue(35); } catch(e){}

    // לוגו: עיגול סגול + B
    var logoBg = addCircle(W/2, 700, 160, PURPLE, 0, DUR);
    scalePop(logoBg, 0);

    var logoB = addText("B", 190, WHITE, W/2, 760, 0, DUR);
    scalePop(logoB, 4/FPS);
    try { logoB.property("Opacity").setValue(100); } catch(e){}

    // Boostly
    var brandTxt = addText("Boostly", 130, WHITE, W/2, 960, 0, DUR);
    fadeIn(brandTxt, 8/FPS, 20);
    slideUp(brandTxt, 8/FPS, 50);

    var tagTxt = addText("הגדל את הנוכחות שלך ברשת", 58, LGRAY, W/2, 1080, 0, 5);
    fadeIn(tagTxt, 22/FPS, 18);

    var badge = addText("המחירים הזולים בישראל", 44, GOLD, W/2, 1175, 0, 5);
    fadeIn(badge, 30/FPS, 15);

    // ════════════════════════════════════════════════════
    //  SCENE 2 — הבעיה  (5-9 שניות)
    // ════════════════════════════════════════════════════
    var s2bg = addRect(W/2, H/2, W, H, DPURP, 5, 9, 0);
    fadeIn(s2bg, 5, 8);

    var s2title = addText("מה הבעיה?", 100, PINK, W/2, 480, 5, 9);
    fadeIn(s2title, 5, 12);
    slideUp(s2title, 5, 60);

    addLine(590, 5, 9);

    var pains = [
        "הפוסטים שלך לא מגיעים לאף אחד",
        "החשבון תקוע ללא עוקבים חדשים",
        "המתחרים עולים עליך ברשתות"
    ];
    var painColors = [WHITE, WHITE, WHITE];
    for (var pi = 0; pi < pains.length; pi++) {
        var pDelay = 5 + (pi * 0.5);
        var pL = addText(pains[pi], 56, painColors[pi], W/2, 730 + pi * 150, 5, 9);
        fadeIn(pL, pDelay, 12);
        slideUp(pL, pDelay, 40);
    }

    // ════════════════════════════════════════════════════
    //  SCENE 3 — הפתרון  (9-14 שניות)
    // ════════════════════════════════════════════════════
    var s3title = addText("הפתרון - Boostly", 100, WHITE, W/2, 460, 9, 14);
    fadeIn(s3title, 9, 12);
    slideUp(s3title, 9, 60);

    addLine(570, 9, 14);

    var solutions = [
        { text: "עוקבים אמיתיים תוך דקות",   color: GREEN },
        { text: "לייקים, צפיות ותגובות",       color: GREEN },
        { text: "אינסטגרם, טיקטוק, יוטיוב",   color: GREEN },
        { text: "תוצאות מיידיות - מובטח",      color: GOLD  }
    ];
    for (var si = 0; si < solutions.length; si++) {
        var sDelay = 9 + 0.3 + si * 0.45;
        var sL = addText(solutions[si].text, 60, solutions[si].color, W/2, 700 + si * 145, 9, 14);
        fadeIn(sL, sDelay, 12);
        slideUp(sL, sDelay, 40);
    }

    // ════════════════════════════════════════════════════
    //  SCENE 4 — מחירים  (14-19 שניות)
    // ════════════════════════════════════════════════════
    var s4bg = addRect(W/2, H/2, W, H, DPURP, 14, 19, 0);
    fadeIn(s4bg, 14, 8);

    var s4title = addText("בחר חבילה", 100, WHITE, W/2, 400, 14, 19);
    fadeIn(s4title, 14, 12);
    slideUp(s4title, 14, 60);

    var s4sub = addText("עוקבים לאינסטגרם", 55, LGRAY, W/2, 490, 14, 19);
    fadeIn(s4sub, 14 + 10/FPS, 12);

    addLine(560, 14, 19);

    var pkgs = [
        { amount: "500   עוקבים",   price: "9.90 ש\"ח",   y: 680  },
        { amount: "1,000 עוקבים",   price: "17.90 ש\"ח",  y: 840  },
        { amount: "2,500 עוקבים",   price: "39.90 ש\"ח",  y: 1000 },
        { amount: "5,000 עוקבים",   price: "69.90 ש\"ח",  y: 1160 }
    ];

    for (var ki = 0; ki < pkgs.length; ki++) {
        var pkg    = pkgs[ki];
        var kDelay = 14 + 0.25 + ki * 0.35;

        // רקע כרטיסיה
        var cardBg = addRect(W/2, pkg.y, 920, 120, [0.14, 0.05, 0.26], kDelay, 19, 22);
        fadeIn(cardBg, kDelay, 8);

        // כמות (ימין)
        var amtL = addText(pkg.amount, 52, WHITE, 340, pkg.y + 10, kDelay, 19);
        fadeIn(amtL, kDelay, 8);
        try { amtL.property("Position").setValue([300, pkg.y + 10]); } catch(e){}

        // מחיר (שמאל)
        var priceL = addText(pkg.price, 58, GOLD, 720, pkg.y + 10, kDelay, 19);
        fadeIn(priceL, kDelay, 8);
        try { priceL.property("Position").setValue([740, pkg.y + 10]); } catch(e){}
    }

    // "הכי נמכר" תג על חבילה 2
    var hotTag = addText("הכי נמכר  ", 36, DARK, W/2 + 300, pkgs[1].y - 38, 14 + 0.6, 19);
    fadeIn(hotTag, 14 + 0.6, 8);
    var hotBg = addRect(W/2 + 300, pkgs[1].y - 38, 180, 44, PINK, 14 + 0.6, 19, 22);
    fadeIn(hotBg, 14 + 0.6, 8);
    try { hotBg.moveAfter(hotTag); } catch(e){}

    // ════════════════════════════════════════════════════
    //  SCENE 5 — סטטיסטיקות  (19-23 שניות)
    // ════════════════════════════════════════════════════
    var s5title = addText("המספרים שלנו", 96, WHITE, W/2, 440, 19, 23);
    fadeIn(s5title, 19, 12);
    slideUp(s5title, 19, 60);

    addLine(540, 19, 23);

    var stats = [
        { big: "5,000+",  sub: "לקוחות מרוצים",  y: 730  },
        { big: "99%",     sub: "שביעות רצון",     y: 1000 },
        { big: "3 דק׳",  sub: "זמן אספקה ממוצע", y: 1270 }
    ];

    for (var sti = 0; sti < stats.length; sti++) {
        var st      = stats[sti];
        var stDelay = 19 + sti * 0.7;

        var bigL = addText(st.big, 120, PINK, W/2, st.y, stDelay, 23);
        scalePop(bigL, stDelay);

        var subL = addText(st.sub, 52, LGRAY, W/2, st.y + 95, stDelay + 12/FPS, 23);
        fadeIn(subL, stDelay + 12/FPS, 12);
    }

    // ════════════════════════════════════════════════════
    //  SCENE 6 — CTA  (23-27 שניות)
    // ════════════════════════════════════════════════════
    var s6bg = addRect(W/2, H/2, W, H, [0.06, 0.01, 0.15], 23, DUR, 0);
    fadeIn(s6bg, 23, 8);

    // זוהר מרכזי
    var s6glow = addCircle(W/2, 820, 400, [0.30, 0.05, 0.55], 23, DUR);
    try { s6glow.property("Opacity").setValue(25); } catch(e){}
    fadeIn(s6glow, 23, 10);

    var ctaHead = addText("מוכן להצליח?", 110, WHITE, W/2, 550, 23, DUR);
    fadeIn(ctaHead, 23, 12);
    slideUp(ctaHead, 23, 60);

    var ctaSub = addText("הצטרף ל-5,000 לקוחות מרוצים", 58, LGRAY, W/2, 660, 23 + 12/FPS, DUR);
    fadeIn(ctaSub, 23 + 12/FPS, 12);

    // כפתור CTA
    var ctaBtn = addRect(W/2, 850, 820, 140, PURPLE, 23 + 20/FPS, DUR, 40);
    scalePop(ctaBtn, 23 + 20/FPS);

    var ctaBtnTxt = addText("התחל עכשיו", 72, WHITE, W/2, 858, 23 + 22/FPS, DUR);
    scalePop(ctaBtnTxt, 23 + 22/FPS);

    // URL
    var urlTxt = addText("boostlyshop.com", 56, GOLD, W/2, 990, 23 + 30/FPS, DUR);
    fadeIn(urlTxt, 23 + 30/FPS, 15);

    // לוגו תחתון
    var finalLogo = addText("Boostly", 80, WHITE, W/2, 1150, 23 + 20/FPS, DUR);
    fadeIn(finalLogo, 23 + 20/FPS, 15);

    // ════════════════════════════════════════════════════
    //  פתיחת הקומפוזיציה + רינדור
    // ════════════════════════════════════════════════════
    app.endUndoGroup();
    comp.openInViewer();

    try {
        var rq  = app.project.renderQueue;
        var rqi = rq.items.add(comp);
        var om  = rqi.outputModule(1);

        var formats = [
            "H.264 - Match Render Settings - 15 Mbps",
            "H.264 High Quality",
            "H.264",
            "MPEG4"
        ];
        var ok = false;
        for (var mi = 0; mi < formats.length; mi++) {
            try { om.applyTemplate(formats[mi]); ok = true; break; } catch(e){}
        }
        if (!ok) { try { om.applyTemplate("QuickTime"); } catch(e){} }

        var out = "C:/Users/arelk/Downloads/boostly_pro.mp4";
        om.file = new File(out);
        rq.render();

        alert("הסרטון רונדר בהצלחה!\nנשמר ב: " + out);

    } catch (rErr) {
        alert(
            "הקומפוזיציה מוכנה!\n\n" +
            "לרינדור ידני:\n" +
            "1. Ctrl+M  (Add to Render Queue)\n" +
            "2. לחץ על 'Lossless' > Format: H.264\n" +
            "3. Output To: בחר תיקיית Downloads\n" +
            "4. לחץ Render\n\n" +
            "שגיאה: " + rErr.toString()
        );
    }

    } catch (err) {
        app.endUndoGroup();
        alert("שגיאה ראשית: " + err.toString() + "\nLine: " + (err.line || "?"));
    }
})();
