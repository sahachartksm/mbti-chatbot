package questions

// Question — คำถาม 1 ข้อ
type Question struct {
	ID      int       `json:"id"`
	Text    LangText  `json:"text"`
	Choices []Choice  `json:"choices"`
	Mapping []Mapping `json:"-"` // ไม่ส่งให้ frontend
}

type LangText struct {
	TH string `json:"th"`
	EN string `json:"en"`
}

type Choice struct {
	ID   string   `json:"id"`
	Text LangText `json:"text"`
}

// Mapping — เมื่อเลือก choice นี้ ให้บวกคะแนนฝั่งใดของ dimension ใด เท่าไหร่
type Mapping struct {
	Choice    string  // "a"
	Dim       string  // "EI" | "SN" | "TF" | "JP"
	Direction string  // "E" | "I" | "S" | "N" | ...
	Weight    float64 // 0.5 | 1.0
}

// ClientView — version ที่จะ serialize ให้ frontend ตาม lang
type ClientQuestion struct {
	ID      int            `json:"id"`
	Text    string         `json:"text"`
	Choices []ClientChoice `json:"choices"`
}
type ClientChoice struct {
	ID   string `json:"id"`
	Text string `json:"text"`
}

// ToClientView — แปลง Questions → client view ตามภาษา
func ToClientView(lang string) []ClientQuestion {
	out := make([]ClientQuestion, 0, len(Questions))
	for _, q := range Questions {
		cq := ClientQuestion{ID: q.ID, Text: pick(q.Text, lang)}
		for _, c := range q.Choices {
			cq.Choices = append(cq.Choices, ClientChoice{ID: c.ID, Text: pick(c.Text, lang)})
		}
		out = append(out, cq)
	}
	return out
}
func pick(t LangText, lang string) string {
	if lang == "en" {
		return t.EN
	}
	return t.TH
}

// Total returns total number of questions
func Total() int { return len(Questions) }

// FindChoice returns mapping for (questionID, choiceID) or nil
func FindChoice(qid int, choice string) *Mapping {
	for _, q := range Questions {
		if q.ID != qid {
			continue
		}
		for _, m := range q.Mapping {
			if m.Choice == choice {
				return &m
			}
		}
	}
	return nil
}

// ------------ Question Bank (20 ข้อ, 5 คำถาม × 4 dimensions) ------------

var Questions = []Question{
	// -------- EI (5 คำถาม) --------
	{
		ID: 1,
		Text: LangText{
			TH: "ในงานปาร์ตี้ คุณมักจะ...",
			EN: "At a party, you tend to...",
		},
		Choices: []Choice{
			{"a", LangText{"เข้าหาและพูดคุยกับคนใหม่ๆ", "Approach and chat with new people"}},
			{"b", LangText{"คุยกับเพื่อนสนิทไม่กี่คน", "Talk with a few close friends"}},
			{"c", LangText{"สังเกตดูเป็นหลัก", "Mostly observe"}},
		},
		Mapping: []Mapping{
			{"a", "EI", "E", 1.0},
			{"b", "EI", "I", 0.5},
			{"c", "EI", "I", 1.0},
		},
	},
	{
		ID: 2,
		Text: LangText{
			TH: "หลังวันทำงานเหนื่อยๆ คุณชาร์จพลังโดย...",
			EN: "After a tiring workday, you recharge by...",
		},
		Choices: []Choice{
			{"a", LangText{"ออกไปเจอเพื่อน", "Going out with friends"}},
			{"b", LangText{"อยู่บ้านคนเดียวเงียบๆ", "Staying alone at home"}},
		},
		Mapping: []Mapping{
			{"a", "EI", "E", 1.0},
			{"b", "EI", "I", 1.0},
		},
	},
	{
		ID: 3,
		Text: LangText{
			TH: "ในประชุมทีม คุณมักจะ...",
			EN: "In team meetings, you usually...",
		},
		Choices: []Choice{
			{"a", LangText{"พูดแสดงความคิดเห็นบ่อย", "Speak up frequently"}},
			{"b", LangText{"ฟังและพูดเมื่อจำเป็น", "Listen and speak only when necessary"}},
		},
		Mapping: []Mapping{
			{"a", "EI", "E", 1.0},
			{"b", "EI", "I", 1.0},
		},
	},
	{
		ID: 4,
		Text: LangText{
			TH: "คุณรู้สึกอย่างไรกับการพูดคุยกับคนแปลกหน้า?",
			EN: "How do you feel about talking to strangers?",
		},
		Choices: []Choice{
			{"a", LangText{"สนุก ชอบ", "Fun and enjoyable"}},
			{"b", LangText{"เฉยๆ ขึ้นอยู่กับสถานการณ์", "Neutral, depends on situation"}},
			{"c", LangText{"รู้สึกเครียดเล็กน้อย", "Slightly stressful"}},
		},
		Mapping: []Mapping{
			{"a", "EI", "E", 1.0},
			{"b", "EI", "I", 0.3},
			{"c", "EI", "I", 1.0},
		},
	},
	{
		ID: 5,
		Text: LangText{
			TH: "ถ้าเลือกวันหยุดได้ คุณจะ...",
			EN: "If you could choose your weekend, you would...",
		},
		Choices: []Choice{
			{"a", LangText{"ออกไปเที่ยวกับกลุ่มเพื่อน", "Go out with a group of friends"}},
			{"b", LangText{"อ่านหนังสือหรือดูหนังอยู่บ้าน", "Read or watch movies at home"}},
		},
		Mapping: []Mapping{
			{"a", "EI", "E", 1.0},
			{"b", "EI", "I", 1.0},
		},
	},

	// -------- SN (5 คำถาม) --------
	{
		ID: 6,
		Text: LangText{
			TH: "เวลาเรียนรู้สิ่งใหม่ คุณชอบ...",
			EN: "When learning something new, you prefer...",
		},
		Choices: []Choice{
			{"a", LangText{"ขั้นตอนชัดเจน ตัวอย่างจริง", "Clear steps and concrete examples"}},
			{"b", LangText{"เข้าใจหลักการและภาพรวม", "Understanding principles and big picture"}},
		},
		Mapping: []Mapping{
			{"a", "SN", "S", 1.0},
			{"b", "SN", "N", 1.0},
		},
	},
	{
		ID: 7,
		Text: LangText{
			TH: "คุณสนใจ...",
			EN: "You are more interested in...",
		},
		Choices: []Choice{
			{"a", LangText{"รายละเอียดที่จับต้องได้", "Tangible details"}},
			{"b", LangText{"ความเป็นไปได้และไอเดียใหม่", "Possibilities and new ideas"}},
		},
		Mapping: []Mapping{
			{"a", "SN", "S", 1.0},
			{"b", "SN", "N", 1.0},
		},
	},
	{
		ID: 8,
		Text: LangText{
			TH: "เพื่อนบอกว่าคุณเป็นคน...",
			EN: "Friends describe you as someone who is...",
		},
		Choices: []Choice{
			{"a", LangText{"ปฏิบัติจริง ไม่ฟุ้ง", "Practical and grounded"}},
			{"b", LangText{"ช่างจินตนาการ", "Imaginative"}},
			{"c", LangText{"ทั้งสองอย่างพอๆ กัน", "Both equally"}},
		},
		Mapping: []Mapping{
			{"a", "SN", "S", 1.0},
			{"b", "SN", "N", 1.0},
			{"c", "SN", "N", 0.3},
		},
	},
	{
		ID: 9,
		Text: LangText{
			TH: "เวลาทำโปรเจค คุณให้ความสำคัญกับ...",
			EN: "When working on a project, you focus on...",
		},
		Choices: []Choice{
			{"a", LangText{"การทำปัจจุบันให้ดี", "Doing the present task well"}},
			{"b", LangText{"วิสัยทัศน์ระยะยาว", "Long-term vision"}},
		},
		Mapping: []Mapping{
			{"a", "SN", "S", 1.0},
			{"b", "SN", "N", 1.0},
		},
	},
	{
		ID: 10,
		Text: LangText{
			TH: "ข้อความไหนใกล้เคียงกับคุณมากกว่า?",
			EN: "Which statement is closer to you?",
		},
		Choices: []Choice{
			{"a", LangText{"เชื่อในสิ่งที่เห็นและจับต้องได้", "Believe what you can see and touch"}},
			{"b", LangText{"สนใจความหมายที่ซ่อนอยู่", "Interested in hidden meanings"}},
		},
		Mapping: []Mapping{
			{"a", "SN", "S", 1.0},
			{"b", "SN", "N", 1.0},
		},
	},

	// -------- TF (5 คำถาม) --------
	{
		ID: 11,
		Text: LangText{
			TH: "เวลาตัดสินใจเรื่องสำคัญ คุณพึ่ง...",
			EN: "When making important decisions, you rely on...",
		},
		Choices: []Choice{
			{"a", LangText{"ตรรกะและข้อมูล", "Logic and data"}},
			{"b", LangText{"ความรู้สึกและผลต่อคน", "Feelings and impact on people"}},
		},
		Mapping: []Mapping{
			{"a", "TF", "T", 1.0},
			{"b", "TF", "F", 1.0},
		},
	},
	{
		ID: 12,
		Text: LangText{
			TH: "เพื่อนร้องไห้เล่าเรื่องเศร้าให้ฟัง คุณมักจะ...",
			EN: "A friend cries about their sad story, you tend to...",
		},
		Choices: []Choice{
			{"a", LangText{"เสนอวิธีแก้ปัญหา", "Offer solutions"}},
			{"b", LangText{"โอบกอดและรับฟัง", "Hug and listen"}},
		},
		Mapping: []Mapping{
			{"a", "TF", "T", 1.0},
			{"b", "TF", "F", 1.0},
		},
	},
	{
		ID: 13,
		Text: LangText{
			TH: "คุณเคารพคน...",
			EN: "You respect people who are...",
		},
		Choices: []Choice{
			{"a", LangText{"ฉลาด มีเหตุผล", "Smart and logical"}},
			{"b", LangText{"อบอุ่น เห็นใจผู้อื่น", "Warm and empathetic"}},
		},
		Mapping: []Mapping{
			{"a", "TF", "T", 1.0},
			{"b", "TF", "F", 1.0},
		},
	},
	{
		ID: 14,
		Text: LangText{
			TH: "ถ้าต้องวิจารณ์งานเพื่อน คุณจะ...",
			EN: "When critiquing a friend's work, you...",
		},
		Choices: []Choice{
			{"a", LangText{"บอกตรงๆ เพื่อพัฒนา", "Tell them directly to improve"}},
			{"b", LangText{"นุ่มนวล รักษาความรู้สึก", "Be gentle, preserve feelings"}},
			{"c", LangText{"ตรงไปตรงมาแต่ใส่ใจคำพูด", "Direct but mindful of words"}},
		},
		Mapping: []Mapping{
			{"a", "TF", "T", 1.0},
			{"b", "TF", "F", 1.0},
			{"c", "TF", "T", 0.4},
		},
	},
	{
		ID: 15,
		Text: LangText{
			TH: "ในการประชุม สิ่งที่สำคัญที่สุดคือ...",
			EN: "In a meeting, the most important thing is...",
		},
		Choices: []Choice{
			{"a", LangText{"การตัดสินใจที่ถูกต้อง", "Making the right decision"}},
			{"b", LangText{"ทุกคนรู้สึกได้รับการรับฟัง", "Everyone feels heard"}},
		},
		Mapping: []Mapping{
			{"a", "TF", "T", 1.0},
			{"b", "TF", "F", 1.0},
		},
	},

	// -------- JP (5 คำถาม) --------
	{
		ID: 16,
		Text: LangText{
			TH: "เวลาเดินทาง คุณมักจะ...",
			EN: "When traveling, you usually...",
		},
		Choices: []Choice{
			{"a", LangText{"วางแผนทุกวันล่วงหน้า", "Plan every day in advance"}},
			{"b", LangText{"ตัดสินใจหน้างาน", "Decide on the spot"}},
		},
		Mapping: []Mapping{
			{"a", "JP", "J", 1.0},
			{"b", "JP", "P", 1.0},
		},
	},
	{
		ID: 17,
		Text: LangText{
			TH: "โต๊ะทำงานของคุณ...",
			EN: "Your workspace is...",
		},
		Choices: []Choice{
			{"a", LangText{"เป็นระเบียบเสมอ", "Always organized"}},
			{"b", LangText{"รกตามความคิดสร้างสรรค์", "Messy, creatively"}},
			{"c", LangText{"ผสมๆ แล้วแต่ช่วง", "Mixed, depends"}},
		},
		Mapping: []Mapping{
			{"a", "JP", "J", 1.0},
			{"b", "JP", "P", 1.0},
			{"c", "JP", "P", 0.4},
		},
	},
	{
		ID: 18,
		Text: LangText{
			TH: "Deadlines คุณ...",
			EN: "With deadlines, you...",
		},
		Choices: []Choice{
			{"a", LangText{"ทำเสร็จก่อนเวลาเสมอ", "Always finish ahead of time"}},
			{"b", LangText{"ทำนาทีสุดท้ายได้ดีที่สุด", "Work best at the last minute"}},
		},
		Mapping: []Mapping{
			{"a", "JP", "J", 1.0},
			{"b", "JP", "P", 1.0},
		},
	},
	{
		ID: 19,
		Text: LangText{
			TH: "คุณรู้สึกอย่างไรเมื่อแผนเปลี่ยนกระทันหัน?",
			EN: "How do you feel about sudden plan changes?",
		},
		Choices: []Choice{
			{"a", LangText{"ไม่ชอบ กระทบ routine", "Dislike it, disrupts routine"}},
			{"b", LangText{"ตื่นเต้น ชอบสิ่งใหม่", "Excited, love surprises"}},
		},
		Mapping: []Mapping{
			{"a", "JP", "J", 1.0},
			{"b", "JP", "P", 1.0},
		},
	},
	{
		ID: 20,
		Text: LangText{
			TH: "ข้อความที่ตรงกับคุณที่สุด...",
			EN: "Which fits you best...",
		},
		Choices: []Choice{
			{"a", LangText{"ตัดสินใจเร็ว เดินหน้า", "Decide quickly, move on"}},
			{"b", LangText{"เปิดทางเลือกไว้ก่อน", "Keep options open"}},
		},
		Mapping: []Mapping{
			{"a", "JP", "J", 1.0},
			{"b", "JP", "P", 1.0},
		},
	},
}
