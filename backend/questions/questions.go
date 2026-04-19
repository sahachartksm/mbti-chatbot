// Package questions — 10 open-ended interview questions for LLM-based MBTI analysis.
// คำถามปลายเปิด 10 ข้อ ครอบคลุมทั้ง 4 มิติของ MBTI (EI / SN / TF / JP)
// ผู้ใช้พิมพ์คำตอบเป็นข้อความอิสระ (ไทย / อังกฤษ)
package questions

// LangText — bilingual text
type LangText struct {
	TH string `json:"th"`
	EN string `json:"en"`
}

// Question — คำถามปลายเปิด 1 ข้อ
type Question struct {
	ID       int      `json:"id"`
	Text     LangText `json:"text"`
	Hint     LangText `json:"hint"`     // คำแนะนำช่วยตอบ
	Dimension string  `json:"dimension"` // "EI" | "SN" | "TF" | "JP" | "MIX"
}

// ClientQuestion — shape ที่ส่งให้ frontend ตามภาษา
type ClientQuestion struct {
	ID        int    `json:"id"`
	Text      string `json:"text"`
	Hint      string `json:"hint"`
	Dimension string `json:"dimension"`
}

// ToClientView — serialize ตาม lang
func ToClientView(lang string) []ClientQuestion {
	out := make([]ClientQuestion, 0, len(Questions))
	for _, q := range Questions {
		out = append(out, ClientQuestion{
			ID:        q.ID,
			Text:      pick(q.Text, lang),
			Hint:      pick(q.Hint, lang),
			Dimension: q.Dimension,
		})
	}
	return out
}

func pick(t LangText, lang string) string {
	if lang == "en" {
		return t.EN
	}
	return t.TH
}

// Total — จำนวนคำถามทั้งหมด
func Total() int { return len(Questions) }

// FindByID returns the question with the given ID, or nil.
func FindByID(id int) *Question {
	for i := range Questions {
		if Questions[i].ID == id {
			return &Questions[i]
		}
	}
	return nil
}

// TextFor returns the question's text in the given language, or empty if not found.
func TextFor(id int, lang string) string {
	if q := FindByID(id); q != nil {
		return pick(q.Text, lang)
	}
	return ""
}

// ----------------------- Question Bank (10 ข้อ) -----------------------

var Questions = []Question{
	{
		ID:        1,
		Dimension: "EI",
		Text: LangText{
			TH: "เล่าให้ฟังว่าคุณชอบใช้เวลาว่างอย่างไร และคุณ “ชาร์จพลัง” ได้ดีที่สุดในสถานการณ์แบบไหน?",
			EN: "Tell me how you like to spend your free time, and in what kind of situation do you feel most recharged?",
		},
		Hint: LangText{
			TH: "ลองเล่าถึงกิจกรรมจริง ๆ เช่น อยู่คนเดียว / อยู่กับเพื่อน / ออกไปข้างนอก / ทำงานอดิเรก",
			EN: "Concrete activities help — e.g. alone, with friends, going out, hobbies.",
		},
	},
	{
		ID:        2,
		Dimension: "EI",
		Text: LangText{
			TH: "คุณรู้สึกอย่างไรเวลาต้องพบคนใหม่หรือเข้าสังคมกลุ่มใหญ่? ยกตัวอย่างเหตุการณ์ล่าสุดที่จำได้",
			EN: "How do you feel about meeting new people or being in large social gatherings? Share a recent real example.",
		},
		Hint: LangText{
			TH: "เล่าเหตุการณ์จริง อารมณ์ที่เกิดขึ้น และคุณทำอะไรไปบ้าง",
			EN: "Describe what happened, what you felt, and how you acted.",
		},
	},
	{
		ID:        3,
		Dimension: "SN",
		Text: LangText{
			TH: "เวลาเจอปัญหาหรือสิ่งใหม่ ๆ ที่ไม่เคยเจอ คุณเริ่มต้นคิดและจัดการอย่างไร? ยกตัวอย่างประกอบ",
			EN: "When you face a brand-new problem, how do you start thinking and approaching it? Give an example.",
		},
		Hint: LangText{
			TH: "เจาะที่ขั้นตอนแรก ๆ เช่น หาข้อมูล วางแผน ลองทำ หรือคิดภาพรวมก่อน",
			EN: "Focus on your first steps — research, plan, experiment, or see the big picture.",
		},
	},
	{
		ID:        4,
		Dimension: "SN",
		Text: LangText{
			TH: "คุณชอบเรียนรู้สิ่งใหม่แบบไหนมากกว่า — จากข้อเท็จจริงที่จับต้องได้และตัวอย่างจริง หรือจากแนวคิด ทฤษฎี และความเป็นไปได้?",
			EN: "Which way do you prefer to learn — from concrete facts and real examples, or from concepts, theories, and possibilities?",
		},
		Hint: LangText{
			TH: "อธิบายเหตุผล และยกตัวอย่างเรื่องที่เคยเรียนรู้แล้วสนุก",
			EN: "Explain why, and give an example of a topic you enjoyed learning.",
		},
	},
	{
		ID:        5,
		Dimension: "TF",
		Text: LangText{
			TH: "เล่าถึงการตัดสินใจสำคัญครั้งล่าสุดของคุณ คุณใช้อะไรเป็นเกณฑ์หลัก และผลลัพธ์เป็นอย่างไร?",
			EN: "Tell me about a recent important decision you made. What was your main criterion, and how did it turn out?",
		},
		Hint: LangText{
			TH: "ลองชี้ว่าคุณชั่งน้ำหนัก “ตรรกะและข้อมูล” หรือ “ผลกระทบต่อคน / ความรู้สึก” มากกว่ากัน",
			EN: "Point out whether you weighed logic/data or people/feelings more.",
		},
	},
	{
		ID:        6,
		Dimension: "TF",
		Text: LangText{
			TH: "เวลาเพื่อนสนิทมาปรึกษาเรื่องหนักใจ คุณตอบสนองและให้คำแนะนำแบบไหน?",
			EN: "When a close friend confides a difficult problem, how do you respond and advise?",
		},
		Hint: LangText{
			TH: "โฟกัสว่าคุณมักเสนอ “ทางแก้” ก่อน หรือ “รับฟังและอยู่ข้าง ๆ” ก่อน",
			EN: "Do you usually offer solutions first, or listen and be present first?",
		},
	},
	{
		ID:        7,
		Dimension: "JP",
		Text: LangText{
			TH: "คุณจัดการชีวิตประจำวันและเป้าหมายระยะยาวอย่างไร? วางแผนล่วงหน้าเยอะแค่ไหน?",
			EN: "How do you manage your daily life and long-term goals? How far ahead do you plan?",
		},
		Hint: LangText{
			TH: "พูดถึงการทำ list, ปฏิทิน, deadline, routine หรือวิธีที่คุณใช้จริง ๆ",
			EN: "Mention to-do lists, calendars, deadlines, routines, or how you actually operate.",
		},
	},
	{
		ID:        8,
		Dimension: "JP",
		Text: LangText{
			TH: "คุณรู้สึกอย่างไรเมื่อแผนเปลี่ยนกะทันหัน หรือเจอสถานการณ์ที่ไม่แน่นอน? คุณรับมืออย่างไร?",
			EN: "How do you feel when plans change suddenly or when a situation is uncertain? How do you cope?",
		},
		Hint: LangText{
			TH: "เล่าเหตุการณ์จริง ปฏิกิริยาในใจ และการกระทำที่ตามมา",
			EN: "Describe a real scenario, your inner reaction, and what you did.",
		},
	},
	{
		ID:        9,
		Dimension: "MIX",
		Text: LangText{
			TH: "อธิบายจุดแข็ง 3 อย่าง และจุดอ่อน 3 อย่างของตัวคุณเองอย่างตรงไปตรงมา พร้อมตัวอย่างจากชีวิตจริง",
			EN: "Honestly list 3 of your strengths and 3 of your weaknesses, with real-life examples.",
		},
		Hint: LangText{
			TH: "ตรงไปตรงมา ไม่ต้องสวยหรู เพราะจะช่วยให้การวิเคราะห์แม่นยำขึ้น",
			EN: "Be candid — honesty improves the accuracy of the analysis.",
		},
	},
	{
		ID:        10,
		Dimension: "MIX",
		Text: LangText{
			TH: "ในอีก 5-10 ปีข้างหน้า คุณอยากเป็นคนแบบไหน? มีค่านิยมอะไรที่คุณให้ความสำคัญที่สุด?",
			EN: "In the next 5-10 years, who do you want to become? What values matter most to you?",
		},
		Hint: LangText{
			TH: "เล่าความฝัน ค่านิยม และสิ่งที่คุณไม่ยอมประนีประนอม",
			EN: "Share your dreams, values, and what you refuse to compromise on.",
		},
	},
}

// โหมดเดิม (20 ข้อ multiple-choice) ถูกลบ — ใช้ 10 ข้อปลายเปิด + LLM แทน
