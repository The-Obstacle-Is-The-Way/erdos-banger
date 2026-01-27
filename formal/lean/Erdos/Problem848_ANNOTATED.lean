/-
Problem 848: Erdős Problem #848 (Erdős-Sárközy) — ANNOTATED FOR ARISTOTLE

This file is a copy of Problem848_COMPLETE.lean with DETAILED COMMENTS from
the paper: Sawhney-Sellke (arXiv:2511.16072), Section 09-SawhneySellke.tex

The paper's proof structure:
  - Lemma 5 (lem:sieve-1): Sieve bound for residue classes
  - Lemma 6 (lem:sf-AP): Squarefree density in arithmetic progressions
  - Proposition 1 (prop:main): The main theorem with casework

SOURCE: literature/cache/arxiv/extracted/2511.16072/content/09-SawhneySellke.tex
-/

-- ============================================================================
-- IMPORTS (Mathlib only - no local imports)
-- ============================================================================

import Mathlib.Data.Finset.Basic
import Mathlib.Data.Nat.Prime.Basic
import Mathlib.Data.Nat.Squarefree
import Mathlib.Data.Nat.Cast.Order.Field
import Mathlib.Algebra.BigOperators.Group.Finset.Basic
import Mathlib.Data.ZMod.Basic
import Mathlib.Data.Real.Basic
import Mathlib.NumberTheory.LegendreSymbol.Basic
import Mathlib.Data.Nat.ModEq

namespace Erdos.Problem848

-- ============================================================================
-- SECTION 1: CORE DEFINITIONS
-- ============================================================================

/-- Problem metadata -/
structure ErdosProblem where
  id : Nat
  title : String
  status : String
  deriving Repr

def problem : ErdosProblem := {
  id := 848
  title := "Erdős-Sárközy Squarefree Products"
  status := "decidable"
}

/-- A set A has the non-squarefree product property if ab+1 is not squarefree
    for all a, b in A. -/
def NonSquarefreeProductProp (A : Finset ℕ) : Prop :=
  ∀ a ∈ A, ∀ b ∈ A, ¬ Squarefree (a * b + 1)

/-- The candidate extremal set: {n ∈ {0,…,N-1} : n ≡ 7 (mod 25)} -/
def A₇ (N : ℕ) : Finset ℕ :=
  (Finset.range N).filter (fun n => n % 25 = 7)

/-- Alternative candidate: {n ∈ {0,…,N-1} : n ≡ 18 (mod 25)} -/
def A₁₈ (N : ℕ) : Finset ℕ :=
  (Finset.range N).filter (fun n => n % 25 = 18)

/-- The diagonal filter: n is a candidate if n² + 1 is not squarefree. -/
def DiagonalCandidates (N : ℕ) : Finset ℕ :=
  (Finset.range N).filter (fun n => ¬ Squarefree (n * n + 1))

/-- Decidability instance for NonSquarefreeProductProp -/
instance instDecidableNonSquarefreeProductProp (A : Finset ℕ) :
    Decidable (NonSquarefreeProductProp A) := by
  unfold NonSquarefreeProductProp
  infer_instance

-- ============================================================================
-- SECTION 2: MOD 25 DIVISIBILITY LEMMAS (PROVED)
-- ============================================================================

/-- Key lemma: If a ≡ b ≡ 7 (mod 25), then 5² | (ab + 1). -/
lemma mod25_divisibility (a b : ℕ) (ha : a % 25 = 7) (hb : b % 25 = 7) :
    25 ∣ (a * b + 1) := by
  have h1 : a * b % 25 = (a % 25) * (b % 25) % 25 := Nat.mul_mod a b 25
  rw [ha, hb] at h1
  have h2 : (7 : ℕ) * 7 % 25 = 24 := by native_decide
  rw [h2] at h1
  have h3 : (a * b + 1) % 25 = 0 := by omega
  exact Nat.dvd_of_mod_eq_zero h3

/-- Same for A₁₈: If a ≡ b ≡ 18 (mod 25), then 5² | (ab + 1). -/
lemma mod25_divisibility_18 (a b : ℕ) (ha : a % 25 = 18) (hb : b % 25 = 18) :
    25 ∣ (a * b + 1) := by
  have h1 : a * b % 25 = (a % 25) * (b % 25) % 25 := Nat.mul_mod a b 25
  rw [ha, hb] at h1
  have h2 : (18 : ℕ) * 18 % 25 = 24 := by native_decide
  rw [h2] at h1
  have h3 : (a * b + 1) % 25 = 0 := by omega
  exact Nat.dvd_of_mod_eq_zero h3

/-- Helper: 25 = 5² -/
lemma twenty_five_eq_five_sq : (25 : ℕ) = 5 ^ 2 := by native_decide

/-- If 25 | n and n > 0, then n is not squarefree. -/
lemma not_squarefree_of_dvd_25 {n : ℕ} (_hn : n > 0) (h : 25 ∣ n) : ¬ Squarefree n := by
  intro hsq
  rw [twenty_five_eq_five_sq] at h
  have hunit : IsUnit (5 : ℕ) := hsq 5 h
  have : (5 : ℕ) = 1 := Nat.isUnit_iff.mp hunit
  omega

/-- A₇ satisfies the non-squarefree product property. -/
theorem A₇_has_property (N : ℕ) : NonSquarefreeProductProp (A₇ N) := by
  intro a ha b hb
  simp only [A₇, Finset.mem_filter] at ha hb
  have hdiv : 25 ∣ (a * b + 1) := mod25_divisibility a b ha.2 hb.2
  have hpos : a * b + 1 > 0 := Nat.succ_pos _
  exact not_squarefree_of_dvd_25 hpos hdiv

/-- A₁₈ also satisfies the non-squarefree product property. -/
theorem A₁₈_has_property (N : ℕ) : NonSquarefreeProductProp (A₁₈ N) := by
  intro a ha b hb
  simp only [A₁₈, Finset.mem_filter] at ha hb
  have hdiv : 25 ∣ (a * b + 1) := mod25_divisibility_18 a b ha.2 hb.2
  have hpos : a * b + 1 > 0 := Nat.succ_pos _
  exact not_squarefree_of_dvd_25 hpos hdiv

-- ============================================================================
-- SECTION 3: SIEVE BUILDING BLOCKS (PROVED)
-- ============================================================================

/-- For a prime `p` with `p ∤ a`, the congruence `p² ∣ (a*b+1)` forces b ≡ -a⁻¹ (mod p²). -/
lemma dvd_pow_two_mul_add_one_iff_zmod_eq_neg_inv
    {p a b : ℕ} (hp : Nat.Prime p) (ha : ¬p ∣ a) :
    p ^ 2 ∣ (a * b + 1) ↔ (b : ZMod (p ^ 2)) = -((a : ZMod (p ^ 2))⁻¹) := by
  set n : ℕ := p ^ 2
  have hcop : Nat.Coprime a n := by
    simpa [n] using hp.coprime_pow_of_not_dvd (m := 2) ha
  have haUnit : IsUnit (a : ZMod n) := (ZMod.isUnit_iff_coprime a n).2 hcop
  constructor
  · intro hdiv
    have hz : ((a * b + 1 : ℕ) : ZMod n) = 0 :=
      (ZMod.natCast_eq_zero_iff (a * b + 1) n).2 hdiv
    have hz' : (a : ZMod n) * (b : ZMod n) + 1 = 0 := by
      simpa [n, Nat.cast_add, Nat.cast_mul, Nat.cast_one] using hz
    have hprod : (a : ZMod n) * (b : ZMod n) = (-1 : ZMod n) := by
      simpa using (eq_neg_of_add_eq_zero_left hz')
    have hb : (b : ZMod n) = (a : ZMod n)⁻¹ * (-1 : ZMod n) := by
      have hb0 := congrArg (fun x : ZMod n => (a : ZMod n)⁻¹ * x) hprod
      have hb1 :
          ((a : ZMod n)⁻¹ * (a : ZMod n)) * (b : ZMod n) =
            (a : ZMod n)⁻¹ * (-1 : ZMod n) := by
        simpa [mul_assoc] using hb0
      simpa [ZMod.inv_mul_of_unit (a : ZMod n) haUnit] using hb1
    simpa [n, mul_comm, mul_left_comm, mul_assoc] using hb
  · intro hb
    have hz' : (a : ZMod n) * (b : ZMod n) + 1 = 0 := by
      simp [hb, ZMod.mul_inv_of_unit (a : ZMod n) haUnit]
    have hz : ((a * b + 1 : ℕ) : ZMod n) = 0 := by
      simpa [n, Nat.cast_add, Nat.cast_mul, Nat.cast_one] using hz'
    exact (ZMod.natCast_eq_zero_iff (a * b + 1) n).1 hz

/-- If p² | n²+1 for prime p, then p ≡ 1 (mod 4) (because -1 must be a QR mod p). -/
lemma prime_sq_divides_implies_one_mod_four (p n : ℕ) (hp : Nat.Prime p) (hp2 : p > 2)
    (hdiv : p ^ 2 ∣ n ^ 2 + 1) : p % 4 = 1 := by
  have hp_ne_two : p ≠ 2 := by omega
  have hp_dvd : p ∣ n ^ 2 + 1 := by
    have hp_div_p2 : p ∣ p ^ 2 := by simp [pow_two]
    exact Nat.dvd_trans hp_div_p2 hdiv
  haveI : Fact p.Prime := ⟨hp⟩
  have h0 : ((n ^ 2 + 1 : ℕ) : ZMod p) = 0 :=
    (ZMod.natCast_eq_zero_iff (n ^ 2 + 1) p).2 hp_dvd
  have hsq : (n : ZMod p) ^ 2 = (-1 : ZMod p) := by
    have : (n : ZMod p) ^ 2 + 1 = 0 := by
      simpa [Nat.cast_add, Nat.cast_pow, Nat.cast_one] using h0
    simpa using (eq_neg_of_add_eq_zero_left this)
  have hne3 : p % 4 ≠ 3 :=
    ZMod.mod_four_ne_three_of_sq_eq_neg_one (p := p) (y := (n : ZMod p)) hsq
  have hp_mod2 : p % 2 = 1 := (Nat.Prime.mod_two_eq_one_iff_ne_two hp).2 hp_ne_two
  have hp_mod4 : p % 4 = 1 ∨ p % 4 = 3 := (Nat.odd_mod_four_iff).1 hp_mod2
  cases hp_mod4 with
  | inl h1 => exact h1
  | inr h3 => exact (hne3 h3).elim

/-- For prime p ≡ 1 (mod 4), there are exactly 2 roots of r² = -1 in ZMod (p²). -/
lemma two_roots_mod_p_squared (p : ℕ) (hp : Nat.Prime p) (hmod : p % 4 = 1) :
    ∃ r₁ r₂ : ZMod (p ^ 2),
      r₁ ≠ r₂ ∧ r₁ ^ 2 = -1 ∧ r₂ ^ 2 = -1 ∧
        ∀ r : ZMod (p ^ 2), r ^ 2 = -1 → r = r₁ ∨ r = r₂ := by
  obtain ⟨r₁, hr₁⟩ : ∃ r₁ : ZMod (p ^ 2), r₁ ^ 2 = -1 := by
    have h_quad_res : ∃ x : ℕ, x ^ 2 ≡ -1 [ZMOD p ^ 2] := by
      have h_hensel : ∀ {p : ℕ}, Nat.Prime p → p % 4 = 1 → ∃ x : ℕ, x ^ 2 ≡ -1 [ZMOD p] := by
        intro p hp hmod
        haveI := Fact.mk hp
        norm_num [← ZMod.intCast_eq_intCast_iff]
        obtain ⟨x, hx⟩ := ZMod.exists_sq_eq_neg_one_iff (p := p)
        exact Exists.elim (hx (by rw [hmod]; decide)) fun x hx =>
          ⟨x.val, by simpa [sq, ← ZMod.intCast_eq_intCast_iff] using hx.symm⟩
      obtain ⟨x, hx⟩ := @h_hensel p hp hmod
      obtain ⟨k, hk⟩ : ∃ k : ℤ, x ^ 2 = k * p - 1 := by
        exact hx.symm.dvd.imp fun k hk => by linarith
      obtain ⟨y, hy⟩ : ∃ y : ℤ, 2 * x * y ≡ -k [ZMOD p] := by
        obtain ⟨y, hy⟩ : ∃ y : ℤ, 2 * x * y ≡ 1 [ZMOD p] := by
          have h_inv : Int.gcd (2 * x) p = 1 := by
            refine' Nat.coprime_comm.mp (hp.coprime_iff_not_dvd.mpr _)
            norm_num [Int.natAbs_mul, Nat.Prime.dvd_mul hp]
            exact
              ⟨Nat.not_dvd_of_pos_of_lt (by norm_num) (by
                    contrapose! hmod
                    interval_cases p <;> trivial),
                fun h => by
                  have :=
                    Int.modEq_zero_iff_dvd.mp
                      (hx.symm.trans
                        (Int.modEq_zero_iff_dvd.mpr <| dvd_pow (Int.natCast_dvd_natCast.mpr h) two_ne_zero))
                  norm_num at this
                  norm_cast at this
                  have := Nat.le_of_dvd (by norm_num) this
                  interval_cases p <;> trivial⟩
          exact Int.mod_coprime h_inv
        exact ⟨y * -k, by simpa [mul_assoc] using hy.mul_right (-k)⟩
      use Int.natAbs (x + y * p)
      rw [Int.modEq_iff_dvd] at *
      obtain ⟨z, hz⟩ := hy
      use z - y ^ 2
      cases abs_cases (x + y * p : ℤ) <;> push_cast [*] <;> nlinarith
    obtain ⟨x, hx⟩ := h_quad_res
    refine ⟨x, ?_⟩
    erw [← ZMod.intCast_eq_intCast_iff] at hx
    simpa using hx
  refine' ⟨r₁, -r₁, _, _, _, _⟩ <;> simp_all +decide [sq]
  · rw [eq_neg_iff_add_eq_zero]
    by_contra h_contra
    have h_r1_zero : r₁ = 0 := by
      have h_r1_zero : (2 : ℕ) * r₁.val ≡ 0 [MOD p ^ 2] := by
        simp_all +decide [← ZMod.natCast_eq_natCast_iff]
        grind
      have h_r1_zero : p ^ 2 ∣ r₁.val := by
        exact
          (Nat.Coprime.dvd_of_dvd_mul_left
              (show Nat.Coprime (p ^ 2) 2 from by
                exact
                  Nat.Coprime.pow_left 2 <|
                    hp.coprime_iff_not_dvd.mpr fun h => by
                      have := Nat.le_of_dvd (by decide) h
                      interval_cases p <;> trivial)
              <| Nat.dvd_of_mod_eq_zero h_r1_zero)
      haveI := Fact.mk hp
      rw [← ZMod.natCast_eq_zero_iff] at h_r1_zero
      aesop
    norm_num [h_r1_zero] at hr₁
    rcases p with (_ | _ | _ | p) <;>
      (cases hr₁; all_goals contradiction)
  · have h_solutions : ∀ r : ZMod (p ^ 2), r ^ 2 = -1 → r = r₁ ∨ r = -r₁ := by
      intro r hr
      have h_eq : (r - r₁) * (r + r₁) = 0 := by grind
      have h_coprime :
          Nat.gcd (p ^ 2) (r - r₁).val = 1 ∨ Nat.gcd (p ^ 2) (r + r₁).val = 1 := by
        have h_coprime : ¬(p ∣ (r - r₁).val ∧ p ∣ (r + r₁).val) := by
          haveI := Fact.mk hp
          simp_all +decide [← ZMod.natCast_eq_zero_iff]
          intro h
          haveI := Fact.mk hp
          simp_all +decide [sub_eq_iff_eq_add, add_eq_zero_iff_eq_neg]
          rw [eq_neg_iff_add_eq_zero]
          have := congr_arg (fun x : ZMod (p ^ 2) => x.val) hr₁
          norm_num [ZMod.val_add, ZMod.val_mul] at this ⊢
          replace this := congr_arg (· % p) this
          norm_num [Nat.add_mod, Nat.mul_mod, Nat.pow_mod] at this
          simp_all +decide [← sq, ← ZMod.natCast_eq_natCast_iff']
          intro H
          rw [← two_mul] at H
          replace H := congr_arg (fun x : ZMod p => x ^ 2) H
          simp_all +decide [mul_pow]
          rcases p with (_ | _ | _ | p) <;> cases H <;> contradiction
        simp_all +decide [Nat.Prime.coprime_iff_not_dvd]
        tauto
      have h_div : (p ^ 2 : ℕ) ∣ (r - r₁).val ∨ (p ^ 2 : ℕ) ∣ (r + r₁).val := by
        have h_div : (p ^ 2 : ℕ) ∣ ((r - r₁).val * (r + r₁).val) := by
          haveI := Fact.mk hp
          simp_all +decide [← ZMod.natCast_eq_zero_iff]
        cases h_coprime with
        | inl hc => exact Or.inr (Nat.Coprime.dvd_of_dvd_mul_left hc h_div)
        | inr hc => exact Or.inl (Nat.Coprime.dvd_of_dvd_mul_right hc h_div)
      haveI := Fact.mk hp
      simp_all +decide [← ZMod.natCast_eq_zero_iff, sub_eq_iff_eq_add, add_eq_zero_iff_eq_neg]
    simpa only [sq] using h_solutions

-- ============================================================================
-- SECTION 4: CROSS-RESIDUE CONSTRAINTS (PROVED)
-- ============================================================================

/-- If a ≡ 7 (mod 25) and b ≢ 7, 18 (mod 25), then 25 ∤ (ab + 1). -/
lemma cross_residue_not_div_25 (a b : ℕ) (ha : a % 25 = 7)
    (hb : b % 25 ≠ 7 ∧ b % 25 ≠ 18) : ¬ (25 ∣ a * b + 1) := by
  intro hdiv
  have h0 : ((a * b + 1 : ℕ) : ZMod 25) = 0 :=
    (ZMod.natCast_eq_zero_iff (a * b + 1) 25).2 hdiv
  have haZ : (a : ZMod 25) = 7 := by
    have : a % 25 = 7 % 25 := by
      simpa [Nat.mod_eq_of_lt (by decide : 7 < 25)] using ha
    exact (ZMod.natCast_eq_natCast_iff' a 7 25).2 this
  have h1 : (7 : ZMod 25) * (b : ZMod 25) + 1 = 0 := by
    have : (a : ZMod 25) * (b : ZMod 25) + 1 = 0 := by
      simpa [Nat.cast_add, Nat.cast_mul, Nat.cast_one] using h0
    simpa [haZ] using this
  have h2 : (7 : ZMod 25) * (b : ZMod 25) = (-1 : ZMod 25) := by
    simpa using (eq_neg_of_add_eq_zero_left h1)
  have h187 : (18 : ZMod 25) * (7 : ZMod 25) = 1 := by native_decide
  have hbZ : (b : ZMod 25) = (7 : ZMod 25) := by
    have hmul : (18 : ZMod 25) * ((7 : ZMod 25) * (b : ZMod 25)) =
        (18 : ZMod 25) * (-1 : ZMod 25) := by
      simpa [mul_assoc] using congrArg (fun x => (18 : ZMod 25) * x) h2
    have hb' : (b : ZMod 25) = (18 : ZMod 25) * (-1 : ZMod 25) := by
      have hmul' : ((18 : ZMod 25) * (7 : ZMod 25)) * (b : ZMod 25) =
          (18 : ZMod 25) * (-1 : ZMod 25) := by
        calc
          ((18 : ZMod 25) * (7 : ZMod 25)) * (b : ZMod 25) =
              (18 : ZMod 25) * ((7 : ZMod 25) * (b : ZMod 25)) := mul_assoc _ _ _
          _ = (18 : ZMod 25) * (-1 : ZMod 25) := hmul
      have : (1 : ZMod 25) * (b : ZMod 25) = (18 : ZMod 25) * (-1 : ZMod 25) := by
        simpa [h187] using hmul'
      simpa using this
    exact hb'.trans (by native_decide : (18 : ZMod 25) * (-1 : ZMod 25) = (7 : ZMod 25))
  have hbmod : b % 25 = 7 := by
    have hb' : b % 25 = 7 % 25 := (ZMod.natCast_eq_natCast_iff' b 7 25).1 hbZ
    simpa [Nat.mod_eq_of_lt (by decide : 7 < 25)] using hb'
  exact hb.1 hbmod

/-- If b ≢ 7, 18 (mod 25), ab+1 not squarefree implies p² | ab+1 for some p ≠ 5. -/
lemma must_have_other_prime_square (a b : ℕ) (ha : a % 25 = 7)
    (hb : b % 25 ≠ 7 ∧ b % 25 ≠ 18) (hnsq : ¬ Squarefree (a * b + 1)) :
    ∃ p : ℕ, Nat.Prime p ∧ p ≠ 5 ∧ p^2 ∣ a * b + 1 := by
  classical
  have hnot : ¬ ∀ p : ℕ, Nat.Prime p → ¬p * p ∣ a * b + 1 := by
    intro hall
    exact hnsq ((Nat.squarefree_iff_prime_squarefree).2 hall)
  push_neg at hnot
  rcases hnot with ⟨p, hp, hpp⟩
  have h25 : ¬ (25 ∣ a * b + 1) := cross_residue_not_div_25 a b ha hb
  have hp2 : p ^ 2 ∣ a * b + 1 := by simpa [pow_two] using hpp
  refine ⟨p, hp, ?_, hp2⟩
  intro hp5
  subst hp5
  have : 25 ∣ a * b + 1 := by simpa [pow_two] using hp2
  exact (h25 this).elim

-- ============================================================================
-- SECTION 5: DENSITY LEMMAS (PROVED)
-- ============================================================================

noncomputable section DensityLemmas

/-- Number of integers < N congruent to r mod m is at most N/m + 1. -/
lemma card_filter_mod_eq_le (N m r : ℕ) :
    ((Finset.range N).filter (fun n => n ≡ r [MOD m])).card ≤ N / m + 1 := by
  have h_set :
      Finset.filter (fun n => n ≡ r [MOD m]) (Finset.range N) ⊆
        Finset.image (fun q => q * m + (r % m)) (Finset.range (N / m + 1)) := by
    intro n hn
    simp_all +decide [Nat.ModEq]
    exact ⟨n / m, Nat.div_le_div_right hn.1.le, by linarith [Nat.mod_add_div n m]⟩
  exact le_trans (Finset.card_le_card h_set) (Finset.card_image_le.trans (by norm_num))

/-- Number of integers < N congruent to r1 or r2 mod m is at most 2N/m + 1. -/
lemma card_filter_mod_pair_le (N m r1 r2 : ℕ) (hm : m > 0) (h_sum : r1 + r2 = m) (h_r1_pos : 0 < r1)
    (h_r2_pos : 0 < r2) (h_ne : r1 ≠ r2) :
    ((Finset.range N).filter (fun n => n ≡ r1 [MOD m] ∨ n ≡ r2 [MOD m])).card ≤ (2 * N : ℚ) / m + 1 := by
  obtain ⟨q, s, hs⟩ : ∃ q s : ℕ, N = q * m + s ∧ s < m := by
    exact ⟨N / m, N % m, by rw [Nat.div_add_mod'], Nat.mod_lt _ hm⟩
  have h_count :
      ((Finset.filter (fun n => n ≡ r1 [MOD m] ∨ n ≡ r2 [MOD m]) (Finset.range N)).card : ℚ) ≤
        2 * q + (if r1 < s then 1 else 0) + (if r2 < s then 1 else 0) := by
    have h_partition :
        Finset.filter (fun n => n ≡ r1 [MOD m] ∨ n ≡ r2 [MOD m]) (Finset.range N) ⊆
          Finset.biUnion (Finset.range q)
              (fun i =>
                Finset.image (fun j => i * m + j)
                  (Finset.filter (fun j => j ≡ r1 [MOD m] ∨ j ≡ r2 [MOD m]) (Finset.range m))) ∪
            (if r1 < s then {q * m + r1} else ∅) ∪ (if r2 < s then {q * m + r2} else ∅) := by
      intro n hn
      simp_all +decide [Nat.ModEq]
      by_cases h_case : n < q * m
      · exact Or.inl
          ⟨n / m, Nat.div_lt_of_lt_mul <| by linarith, n % m,
            ⟨Nat.mod_lt _ hm, by
              simpa
                [Nat.mod_eq_of_lt (show r1 < m from by linarith),
                  Nat.mod_eq_of_lt (show r2 < m from by linarith)] using hn.2⟩,
            by linarith [Nat.mod_add_div n m]⟩
      · cases hn.2 <;> simp_all +decide
        · obtain ⟨k, hk⟩ : ∃ k, n = q * m + k ∧ k < s := by
            exact ⟨n - q * m, by rw [Nat.add_sub_cancel' h_case], by
              rw [tsub_lt_iff_left h_case]
              linarith⟩
          simp_all +decide [Nat.add_mod]
          rw [Nat.mod_eq_of_lt, Nat.mod_eq_of_lt] at * <;> first | linarith | aesop
        · obtain ⟨r, hr⟩ : ∃ r, n = q * m + r ∧ r < s := by
            exact ⟨n - q * m, by rw [Nat.add_sub_cancel' h_case], by
              rw [tsub_lt_iff_left h_case]
              linarith⟩
          simp_all +decide [Nat.mod_eq_of_lt (by linarith : r1 < m), Nat.mod_eq_of_lt (by linarith : r2 < m)]
          split_ifs <;> simp_all +decide
          · exact Or.inr <| Or.inr <| by
              linarith [Nat.mod_eq_of_lt (by linarith : r < m)]
          · linarith [Nat.mod_eq_of_lt (by linarith : r < m)]
          · exact Or.inr (by linarith [Nat.mod_eq_of_lt (by linarith : r < m)])
          · linarith [Nat.mod_eq_of_lt (by linarith : r < m)]
    have h_biUnion_card :
        (Finset.biUnion (Finset.range q)
              (fun i =>
                Finset.image (fun j => i * m + j)
                  (Finset.filter (fun j => j ≡ r1 [MOD m] ∨ j ≡ r2 [MOD m]) (Finset.range m)))).card ≤
          q * (Finset.filter (fun j => j ≡ r1 [MOD m] ∨ j ≡ r2 [MOD m]) (Finset.range m)).card := by
      exact
        le_trans Finset.card_biUnion_le
          (by
            exact
              le_trans (Finset.sum_le_sum fun _ _ => Finset.card_image_le) (by norm_num))
    have h_filter_card :
        (Finset.filter (fun j => j ≡ r1 [MOD m] ∨ j ≡ r2 [MOD m]) (Finset.range m)).card ≤ 2 := by
      have h_filter_card :
          (Finset.filter (fun j => j ≡ r1 [MOD m] ∨ j ≡ r2 [MOD m]) (Finset.range m)).card ≤
            Finset.card ({r1 % m, r2 % m} : Finset ℕ) := by
        refine Finset.card_le_card ?_
        simp_all +decide [Finset.subset_iff, Nat.ModEq]
        exact fun x hx hx' =>
          Or.imp (fun hx'' => by rw [← hx'', Nat.mod_eq_of_lt hx])
            (fun hx'' => by rw [← hx'', Nat.mod_eq_of_lt hx]) hx'
      exact h_filter_card.trans (Finset.card_insert_le _ _) |> le_trans <| by norm_num
    refine' le_trans (Nat.cast_le.mpr (Finset.card_le_card h_partition)) _
    refine' le_trans (Nat.cast_le.mpr (Finset.card_union_le _ _)) _
    exact
      mod_cast
        le_trans (add_le_add (Finset.card_union_le _ _) le_rfl)
          (by split_ifs <;> norm_num <;> nlinarith)
  split_ifs at h_count <;> simp_all +decide [Nat.modEq_iff_dvd]
  · rw [div_add_one, le_div_iff₀] <;> norm_cast at * <;>
      nlinarith only [hs, h_sum, h_count, ‹r1 < s›, ‹r2 < s›]
  · exact
      le_trans h_count
        (by rw [div_add_one, le_div_iff₀] <;> norm_cast <;>
            nlinarith only [hs, h_sum, ‹r1 < s›, ‹s ≤ r2›])
  · exact
      h_count.trans
        (by rw [div_add_one, le_div_iff₀] <;> norm_cast <;> nlinarith only [hs, hm])
  · exact
      le_add_of_le_of_nonneg
        (by
          rw [le_div_iff₀ (by positivity)]
          nlinarith
            [(by norm_cast : (s : ℚ) ≤ r1), (by norm_cast : (s : ℚ) ≤ r2),
              (by norm_cast : (r1 : ℚ) + r2 = m)])
        zero_le_one

/-- Density of {n < N : p² | n²+1} is at most 2/p² + 1/N. -/
lemma density_single_prime (p : ℕ) (hp : Nat.Prime p) (hmod : p % 4 = 1) (N : ℕ) (hN : N > 0) :
    let count := ((Finset.range N).filter (fun n => (p ^ 2 : ℕ) ∣ n ^ 2 + 1)).card
    (count : ℚ) / N ≤ 2 / p ^ 2 + 1 / N := by
  classical
  obtain ⟨r₁, r₂, hr⟩ :
      ∃ r₁ r₂ : ZMod (p ^ 2),
        r₁ ≠ r₂ ∧ r₁ ^ 2 = -1 ∧ r₂ ^ 2 = -1 ∧ ∀ r : ZMod (p ^ 2), r ^ 2 = -1 → r = r₁ ∨ r = r₂ := by
    simpa using two_roots_mod_p_squared p hp hmod
  have h_set_eq :
      {n ∈ Finset.range N | p ^ 2 ∣ n ^ 2 + 1} =
        {n ∈ Finset.range N | n ≡ r₁.val [MOD p ^ 2] ∨ n ≡ r₂.val [MOD p ^ 2]} := by
    ext n
    simp_all +decide [← ZMod.natCast_eq_natCast_iff]
    intro hn
    haveI := Fact.mk hp
    simp_all +decide [← ZMod.natCast_eq_zero_iff]
    grind
  have h_card_filter :
      ((Finset.range N).filter (fun n => n ≡ r₁.val [MOD p ^ 2] ∨ n ≡ r₂.val [MOD p ^ 2])).card ≤
        (2 * N : ℚ) / p ^ 2 + 1 := by
    convert card_filter_mod_pair_le N (p ^ 2) r₁.val r₂.val _ _ _ _ _ using 1 <;> norm_num [Nat.ModEq]
    · exact pow_pos hp.pos 2
    · have h_sum : r₁.val + r₂.val ≡ 0 [MOD p ^ 2] := by
        have h_card_filter : r₁ + r₂ = 0 := by
          have h_sum : r₁ + r₂ = 0 := by
            have h_neg : (-r₁) ^ 2 = -1 := by grind
            have h_char : (2 : ZMod (p ^ 2)) ≠ 0 := by
              intro h
              rcases p with (_ | _ | _ | p) <;> (cases h; all_goals trivial)
            grind
          exact h_sum
        simp_all +decide [← ZMod.natCast_eq_natCast_iff]
        cases p <;> aesop
      rw [Nat.modEq_zero_iff_dvd] at h_sum
      obtain ⟨k, hk⟩ := h_sum
      rcases k with (_ | _ | k) <;> simp_all +decide [Nat.pow_succ', mul_assoc]
      have h_contra : r₁.val < p ^ 2 ∧ r₂.val < p ^ 2 := by
        haveI := Fact.mk hp
        exact ⟨r₁.val_lt, r₂.val_lt⟩
      nlinarith only [hk, h_contra, hp.two_le]
    · grind
    · grind
    · haveI := Fact.mk hp
      exact fun h => hr.1 <| by rw [← ZMod.natCast_zmod_val r₁, ← ZMod.natCast_zmod_val r₂, h]
  have hcard_eq :
      ((Finset.range N).filter (fun n => (p ^ 2 : ℕ) ∣ n ^ 2 + 1)).card =
        ((Finset.range N).filter (fun n => n ≡ r₁.val [MOD p ^ 2] ∨ n ≡ r₂.val [MOD p ^ 2])).card := by
    simpa using congrArg Finset.card h_set_eq
  have hcount_le :
      (((Finset.range N).filter (fun n => (p ^ 2 : ℕ) ∣ n ^ 2 + 1)).card : ℚ) ≤ (2 * N : ℚ) / p ^ 2 + 1 := by
    simpa [hcard_eq] using h_card_filter
  have hdiv :
      (((Finset.range N).filter (fun n => (p ^ 2 : ℕ) ∣ n ^ 2 + 1)).card : ℚ) / N ≤
        ((2 * N : ℚ) / p ^ 2 + 1) / N := by
    exact div_le_div_of_nonneg_right hcount_le (by exact_mod_cast (Nat.zero_le N))
  have hN0 : (N : ℚ) ≠ 0 := by exact_mod_cast (Nat.ne_of_gt hN)
  have hrhs : ((2 * N : ℚ) / p ^ 2 + 1) / (N : ℚ) = (2 : ℚ) / p ^ 2 + 1 / (N : ℚ) := by
    calc
      ((2 * (N : ℚ)) / (p ^ 2 : ℚ) + 1) / (N : ℚ) =
          ((2 * (N : ℚ)) / (p ^ 2 : ℚ)) / (N : ℚ) + 1 / (N : ℚ) := by simp [add_div]
      _ = (2 * (N : ℚ)) / ((p ^ 2 : ℚ) * (N : ℚ)) + 1 / (N : ℚ) := by simp [div_div]
      _ = (2 : ℚ) / (p ^ 2 : ℚ) + 1 / (N : ℚ) := by
            have :
                (2 * (N : ℚ)) / ((p ^ 2 : ℚ) * (N : ℚ)) = (2 : ℚ) / (p ^ 2 : ℚ) := by
              simpa [mul_assoc, mul_left_comm, mul_comm] using
                (mul_div_mul_right (a := (2 : ℚ)) (b := (p ^ 2 : ℚ)) (c := (N : ℚ)) hN0)
            simp [this]
  have := (show
      (((Finset.range N).filter (fun n => (p ^ 2 : ℕ) ∣ n ^ 2 + 1)).card : ℚ) / N ≤
        (2 : ℚ) / p ^ 2 + 1 / N from by simpa [hrhs] using hdiv)
  simpa using this

end DensityLemmas

-- ============================================================================
-- SECTION 6: HELPER LEMMAS (PROVED)
-- ============================================================================

/-- The non-squarefree property is hereditary. -/
lemma nonSquarefreeProductProp_subset {A B : Finset ℕ} (hAB : A ⊆ B)
    (hB : NonSquarefreeProductProp B) : NonSquarefreeProductProp A := by
  intro a ha b hb
  exact hB a (hAB ha) b (hAB hb)

/-- Any set with the property is contained in DiagonalCandidates. -/
lemma prop_implies_diag_candidates (A : Finset ℕ) (N : ℕ) (hAsub : A ⊆ Finset.range N)
    (hAprop : NonSquarefreeProductProp A) : A ⊆ DiagonalCandidates N := by
  intro a ha
  simp only [DiagonalCandidates, Finset.mem_filter]
  constructor
  · exact hAsub ha
  · exact hAprop a ha a ha

/-- 7 × 18 + 1 = 127 is squarefree (it's prime). -/
lemma seven_times_eighteen_plus_one_squarefree : Squarefree (7 * 18 + 1) := by native_decide

/-- {7, 18} does NOT have the property. -/
lemma pair_7_18_fails : ¬ NonSquarefreeProductProp ({7, 18} : Finset ℕ) := by native_decide

/-- {32, 43} DOES have the property (mixing works for this pair!). -/
lemma pair_32_43_works : NonSquarefreeProductProp ({32, 43} : Finset ℕ) := by native_decide

-- ============================================================================
-- SECTION 7: FINITE VERIFICATION (PROVED by native_decide)
-- ============================================================================

/-- Check if a triple has the property -/
def tripleHasProperty (a b c : ℕ) : Bool :=
  !Squarefree (a * a + 1) &&
  !Squarefree (a * b + 1) &&
  !Squarefree (a * c + 1) &&
  !Squarefree (b * a + 1) &&
  !Squarefree (b * b + 1) &&
  !Squarefree (b * c + 1) &&
  !Squarefree (c * a + 1) &&
  !Squarefree (c * b + 1) &&
  !Squarefree (c * c + 1)

def noTripleWorksIn (N : ℕ) : Prop :=
  ∀ a b c : Fin N, a.val < b.val → b.val < c.val →
    tripleHasProperty a.val b.val c.val = false

instance (N : ℕ) : Decidable (noTripleWorksIn N) := by unfold noTripleWorksIn; infer_instance

-- Computed values
lemma A₇_50_card : (A₇ 50).card = 2 := by native_decide
lemma A₇_100_card : (A₇ 100).card = 4 := by native_decide
lemma A₇_200_card : (A₇ 200).card = 8 := by native_decide

lemma diag_cand_50 : DiagonalCandidates 50 = {7, 18, 32, 38, 41, 43} := by native_decide
lemma diag_cand_100 : DiagonalCandidates 100 = {7, 18, 32, 38, 41, 43, 57, 68, 70, 82, 93, 99} := by native_decide

-- Key finite checks
theorem no_triple_works_50 : noTripleWorksIn 50 := by native_decide

lemma no_triple_in_candidates :
    ∀ (s : Finset ℕ), s ⊆ {7, 18, 32, 38, 41, 43} → s.card = 3 → ¬ NonSquarefreeProductProp s := by
  native_decide

lemma no_five_in_candidates_100 :
    ∀ (s : Finset ℕ), s ⊆ {7, 18, 32, 38, 41, 43, 57, 68, 70, 82, 93, 99} →
      s.card = 5 → ¬ NonSquarefreeProductProp s := by
  native_decide

-- Main theorems for small N
theorem problem_848_N50 :
    ∀ A : Finset ℕ, A ⊆ Finset.range 50 → NonSquarefreeProductProp A →
      A.card ≤ (A₇ 50).card := by
  intro A hAsub hAprop
  rw [A₇_50_card]
  have h_sub_cand : A ⊆ DiagonalCandidates 50 := prop_implies_diag_candidates A 50 hAsub hAprop
  rw [diag_cand_50] at h_sub_cand
  by_contra h
  push_neg at h
  have hcard3 : 3 ≤ A.card := h
  have hex : ∃ s : Finset ℕ, s ⊆ A ∧ s.card = 3 := Finset.exists_subset_card_eq hcard3
  obtain ⟨s, hs_sub, hs_card⟩ := hex
  have hs_prop : NonSquarefreeProductProp s := nonSquarefreeProductProp_subset hs_sub hAprop
  have hs_sub_cand : s ⊆ {7, 18, 32, 38, 41, 43} := Finset.Subset.trans hs_sub h_sub_cand
  exact no_triple_in_candidates s hs_sub_cand hs_card hs_prop

theorem problem_848_N100 :
    ∀ A : Finset ℕ, A ⊆ Finset.range 100 → NonSquarefreeProductProp A →
      A.card ≤ (A₇ 100).card := by
  intro A hAsub hAprop
  rw [A₇_100_card]
  have h_sub_cand : A ⊆ DiagonalCandidates 100 := prop_implies_diag_candidates A 100 hAsub hAprop
  rw [diag_cand_100] at h_sub_cand
  by_contra h
  push_neg at h
  have hcard5 : 5 ≤ A.card := h
  have hex : ∃ s : Finset ℕ, s ⊆ A ∧ s.card = 5 := Finset.exists_subset_card_eq hcard5
  obtain ⟨s, hs_sub, hs_card⟩ := hex
  have hs_prop : NonSquarefreeProductProp s := nonSquarefreeProductProp_subset hs_sub hAprop
  have hs_sub_cand : s ⊆ {7, 18, 32, 38, 41, 43, 57, 68, 70, 82, 93, 99} :=
    Finset.Subset.trans hs_sub h_sub_cand
  exact no_five_in_candidates_100 s hs_sub_cand hs_card hs_prop

-- ============================================================================
-- SECTION 8: SAWHNEY'S THEOREM (Research Level - as Prop)
-- ============================================================================

/-- The exact statement from Sawhney (2025), parameterized by constants. -/
def SawhneyMainAt (η : ℝ) (N₀ : ℕ) : Prop :=
  0 < η ∧ η < (1 / 25 : ℝ) ∧
    ∀ N ≥ N₀, ∀ A : Finset ℕ,
      A ⊆ Finset.range N →
      NonSquarefreeProductProp A →
      (A.card : ℝ) ≥ (1/25 - η) * (N : ℝ) →
      (A ⊆ A₇ N ∨ A ⊆ A₁₈ N)

/-- Paper-level existential: there exist η > 0 and N₀ making SawhneyMainAt true. -/
def SawhneyMain : Prop :=
  ∃ η : ℝ, ∃ N₀ : ℕ, SawhneyMainAt η N₀

/-- The Erdős #848 statement for a fixed N. -/
def Problem848Statement (N : ℕ) : Prop :=
  ∀ A : Finset ℕ, A ⊆ Finset.range N → NonSquarefreeProductProp A →
    A.card ≤ (A₇ N).card

-- ============================================================================
-- SECTION 9: GLUE THEOREMS (PROVED - conditional on SawhneyMain)
-- ============================================================================

lemma A₇_card (N : ℕ) : (A₇ N).card = (N + 17) / 25 := by
  classical
  set K : ℕ := (N + 17) / 25
  have hbij : (A₇ N).card = (Finset.range K).card := by
    refine (Finset.card_bij (s := Finset.range K) (t := A₇ N)
      (i := fun k _hk => 25 * k + 7) ?_ ?_ ?_).symm
    · intro k hk
      have hk' : k < K := by simpa [Finset.mem_range] using hk
      have hk1 : k + 1 ≤ K := Nat.succ_le_iff.2 hk'
      have hmul : 25 * (k + 1) ≤ 25 * K := Nat.mul_le_mul_left 25 hk1
      have hK : 25 * K ≤ N + 17 := by simpa [K] using Nat.mul_div_le (N + 17) 25
      have hmul' : 25 * (k + 1) ≤ N + 17 := le_trans hmul hK
      have hlt : 25 * k + 7 < N := by omega
      simp [A₇, Finset.mem_filter, Finset.mem_range, hlt, Nat.add_mod]
    · intro k₁ _hk₁ k₂ _hk₂ h
      have h' : 25 * k₁ = 25 * k₂ := Nat.add_right_cancel h
      exact Nat.mul_left_cancel (by decide : 0 < 25) h'
    · intro a ha
      have ha' : a < N ∧ a % 25 = 7 := by
        simpa [A₇, Finset.mem_filter, Finset.mem_range] using ha
      have ha_eq : 25 * (a / 25) + 7 = a := by
        have h := Nat.mod_add_div a 25
        simpa [ha'.2, Nat.add_comm, Nat.mul_comm, Nat.mul_left_comm, Nat.mul_assoc] using h
      refine ⟨a / 25, ?_, ?_⟩
      · have hlt : 25 * (a / 25) + 7 < N := by simpa [ha_eq] using ha'.1
        have hmul : 25 * ((a / 25) + 1) ≤ N + 17 := by omega
        have hle : a / 25 + 1 ≤ K := by
          have hmul' : (a / 25 + 1) * 25 ≤ N + 17 := by
            simpa [Nat.mul_comm, Nat.mul_left_comm, Nat.mul_assoc] using hmul
          have := (Nat.le_div_iff_mul_le (k0 := (by decide : 0 < 25))).2 hmul'
          simpa [K] using this
        have hltK : a / 25 < K := Nat.lt_of_lt_of_le (Nat.lt_succ_self _) hle
        simpa [Finset.mem_range] using hltK
      · exact ha_eq
  simpa [Finset.card_range, K] using hbij

lemma A₁₈_card (N : ℕ) : (A₁₈ N).card = (N + 6) / 25 := by
  classical
  set K : ℕ := (N + 6) / 25
  have hbij : (A₁₈ N).card = (Finset.range K).card := by
    refine (Finset.card_bij (s := Finset.range K) (t := A₁₈ N)
      (i := fun k _hk => 25 * k + 18) ?_ ?_ ?_).symm
    · intro k hk
      have hk' : k < K := by simpa [Finset.mem_range] using hk
      have hk1 : k + 1 ≤ K := Nat.succ_le_iff.2 hk'
      have hmul : 25 * (k + 1) ≤ 25 * K := Nat.mul_le_mul_left 25 hk1
      have hK : 25 * K ≤ N + 6 := by simpa [K] using Nat.mul_div_le (N + 6) 25
      have hmul' : 25 * (k + 1) ≤ N + 6 := le_trans hmul hK
      have hlt : 25 * k + 18 < N := by omega
      simp [A₁₈, Finset.mem_filter, Finset.mem_range, hlt, Nat.add_mod]
    · intro k₁ _hk₁ k₂ _hk₂ h
      have h' : 25 * k₁ = 25 * k₂ := Nat.add_right_cancel h
      exact Nat.mul_left_cancel (by decide : 0 < 25) h'
    · intro a ha
      have ha' : a < N ∧ a % 25 = 18 := by
        simpa [A₁₈, Finset.mem_filter, Finset.mem_range] using ha
      have ha_eq : 25 * (a / 25) + 18 = a := by
        have h := Nat.mod_add_div a 25
        simpa [ha'.2, Nat.add_comm, Nat.mul_comm, Nat.mul_left_comm, Nat.mul_assoc] using h
      refine ⟨a / 25, ?_, ?_⟩
      · have hlt : 25 * (a / 25) + 18 < N := by simpa [ha_eq] using ha'.1
        have hmul : 25 * ((a / 25) + 1) ≤ N + 6 := by omega
        have hle : a / 25 + 1 ≤ K := by
          have hmul' : (a / 25 + 1) * 25 ≤ N + 6 := by
            simpa [Nat.mul_comm, Nat.mul_left_comm, Nat.mul_assoc] using hmul
          have := (Nat.le_div_iff_mul_le (k0 := (by decide : 0 < 25))).2 hmul'
          simpa [K] using this
        have hltK : a / 25 < K := Nat.lt_of_lt_of_le (Nat.lt_succ_self _) hle
        simpa [Finset.mem_range] using hltK
      · exact ha_eq
  simpa [Finset.card_range, K] using hbij

lemma A₁₈_card_le_A₇ (N : ℕ) : (A₁₈ N).card ≤ (A₇ N).card := by
  have h : N + 6 ≤ N + 17 := Nat.add_le_add_left (by decide : 6 ≤ 17) N
  simpa [A₇_card, A₁₈_card] using Nat.div_le_div_right h

lemma card_gt_A₇_implies_dense {η : ℝ} (hη : 0 < η) {N : ℕ} {A : Finset ℕ}
    (hgt : (A₇ N).card < A.card) :
    (A.card : ℝ) ≥ (1/25 - η) * (N : ℝ) := by
  have hsucc : (A₇ N).card + 1 ≤ A.card := Nat.succ_le_iff.2 hgt
  have hA : ((A₇ N).card + 1 : ℝ) ≤ (A.card : ℝ) := by exact_mod_cast hsucc
  have hA7 : ((N + 17 : ℝ) / 25) < ((A₇ N).card + 1 : ℝ) := by
    have hq : (25 : ℝ) * ((A₇ N).card + 1 : ℝ) > (N + 17 : ℝ) := by
      have hq_nat : 25 * ((A₇ N).card + 1) > N + 17 := by
        have hcard : (A₇ N).card = (N + 17) / 25 := A₇_card N
        have hdiv : 25 * ((N + 17) / 25) + (N + 17) % 25 = N + 17 := Nat.div_add_mod (N + 17) 25
        have hmod : (N + 17) % 25 < 25 := Nat.mod_lt _ (by decide : 0 < 25)
        omega
      exact_mod_cast hq_nat
    nlinarith
  have hN17 : (N + 17 : ℝ) / 25 ≥ (1 / 25 - η) * (N : ℝ) := by nlinarith
  have : (A.card : ℝ) ≥ (N + 17 : ℝ) / 25 := by
    have : (N + 17 : ℝ) / 25 ≤ (A.card : ℝ) := le_trans hA7.le hA
    exact this
  exact le_trans hN17 this

/-- If SawhneyMainAt holds, the conjectured bound holds for all N ≥ N₀. -/
theorem problem_848_large_of_sawhney {η : ℝ} {N₀ : ℕ} (h : SawhneyMainAt η N₀) :
    ∀ N ≥ N₀, Problem848Statement N := by
  classical
  rcases h with ⟨hη, _hηsmall, hmain⟩
  intro N hN A hAsub hAprop
  by_contra hle
  have hgt : (A₇ N).card < A.card := lt_of_not_ge hle
  have hdense : (A.card : ℝ) ≥ (1/25 - η) * (N : ℝ) := card_gt_A₇_implies_dense hη hgt
  have hstruct := hmain N hN A hAsub hAprop hdense
  cases hstruct with
  | inl hsub7 => exact (not_le_of_gt hgt) (Finset.card_le_card hsub7)
  | inr hsub18 =>
      have hcard18 : A.card ≤ (A₁₈ N).card := Finset.card_le_card hsub18
      have h18le7 : (A₁₈ N).card ≤ (A₇ N).card := A₁₈_card_le_A₇ N
      exact (not_le_of_gt hgt) (le_trans hcard18 h18le7)

theorem problem_848_resolved_up_to_finite_check_of_sawhney (h : SawhneyMain) :
    ∃ N₀ : ℕ, ∀ N ≥ N₀, Problem848Statement N := by
  rcases h with ⟨η, N₀, hηN₀⟩
  exact ⟨N₀, problem_848_large_of_sawhney hηN₀⟩

-- ============================================================================
-- SECTION 10: THE BLOCKING THEOREM — PAPER PROOF ANNOTATIONS
-- ============================================================================

/-!
## Paper Source: Sawhney-Sellke, arXiv:2511.16072, Section 09

### Lemma 5 (lem:sieve-1) from Paper:

Let P be a subset of primes with max P ≤ N^{1/2} and let q be a positive integer.
For each p ∈ P, define R_p to denote a set of residue classes modulo p² with |R_p| ≤ 2
and R_p = ∅ if (p,q) ≠ 1. Then:

|{n ∈ [N] : n ≡ t (mod q)} ∩ ⋃_{p∈P} {n (mod p²) ∈ R_p}| - (N/q)(1 - ∏_{p∈P}(1 - |R_p|/p²))|
  ≤ O(N(log N)^{-1/2})

**Proof sketch:**
- Let T = ⌊√(log N)⌋
- Large primes (T ≤ p ≤ N^{1/2}) contribute O(N/T) by union bound
- Small primes (p ≤ T) handled by inclusion-exclusion
- Product ∏_{p≤T} p² ≤ N^{o(1)}, so error is N^{o(1)}

### Lemma 6 (lem:sf-AP) from Paper:

Fix N, residue class t (mod q) with q a perfect square, and integer b with 1 ≤ b ≤ N.
Suppose there is no prime p with p²|q and p²|(bt+1). Then:

|{a ∈ [N] : a ≡ t (mod q) ∧ μ(ab+1) = 0}| - (N/q)(1 - ∏_{(p,qb)=1}(1 - 1/p²))|
  ≤ O(N/√(log N))

**Proof sketch:**
- ab+1 ≤ N²+1, so if μ(ab+1)=0, ∃ prime p with p²|(ab+1)
- (p,qb) = 1: if p|b then p∤ab+1; if p|q then ab+1 ≡ bt+1 ≢ 0 (mod p²)
- Use T = ⌊√(log N)⌋, handle p ≤ T via Lemma 5

### Proposition 1 (prop:main) from Paper:

Let η = 0.002 and N sufficiently large. If |A| ≥ (1/25 - η)N then A ⊆ A₇ or A ⊆ A₁₈.

**Proof structure (CASEWORK):**

Define:
- A₇ = {a ∈ A : a ≡ 7 (mod 25)}
- A₁₈ = {a ∈ A : a ≡ 18 (mod 25)}
- A* = A \ (A₇ ∪ A₁₈)

**Case 1: A* contains an even element b**
For x ∈ A*, need p ≡ 1 (mod 4), p ≥ 13 with p²|x²+1.
By Lemma 5: |A*|/N ≤ (23/25)(1 - ∏_{p≡1(4), p≥13}(1-2/p²)) ≤ 0.0252

For a ∈ A₇ ∪ A₁₈, need p ≠ 2,5 with p²|ab+1.
By Lemma 6: |A₇ ∪ A₁₈|/N ≤ (2/25)(1 - ∏_{p≠2,5}(1-1/p²)) ≤ 0.0125

Total: |A|/N ≤ 0.0252 + 0.0125 = 0.0377 < 0.04 - η. Contradiction!

**Case 2: A* is non-empty but all odd**
|A*|/N ≤ (1/2)(23/25)(1 - ∏_{p≡1(4), p≥13}(1-2/p²)) ≤ 0.0126

Subcase 2a: A₇ ∪ A₁₈ has no even elements
By Lemma 6 on mod 100 classes:
|A₇ ∪ A₁₈|/N ≤ 1/50 + (1/50)(1 - ∏_{p≠2,5}(1-1/p²)) ≤ 0.0200 + 0.0032 = 0.0232
Total: 0.0126 + 0.0232 = 0.0358 < 0.04 - η. Contradiction!

Subcase 2b: A₇ has even element b'
|A₇|/N ≤ (1/25)(1 - ∏_{p≠5}(1-1/p²)) ≤ 0.0147
|A₁₈|/N ≤ (1/25)(1 - ∏_{p≠2,5}(1-1/p²)) ≤ 0.0063
Total: 0.0126 + 0.0147 + 0.0063 = 0.0336 < 0.04 - η. Contradiction!

**Case 3: A* = ∅, but both A₇ and A₁₈ are non-empty**
Fix b ∈ A₇, b' ∈ A₁₈.
|A|/N ≤ (2/25)(1 - ∏_{p≠5}(1-1/p²)) ≤ 0.0294 < 0.04 - η. Contradiction!

**Conclusion:** A ⊆ A₇ or A ⊆ A₁₈.

### Numerical Constants (from paper):
- ∏_p(1-1/p²) = 6/π² ≥ 0.6079, so 1 - 6/π² ≤ 0.3921
- ∏_{p≠5}(1-1/p²) = 25/(4π²) ≥ 0.6332, so 1 - 25/(4π²) ≤ 0.3668
- ∏_{p≠2,5}(1-1/p²) = 25/(3π²) ≥ 0.8443, so 1 - 25/(3π²) ≤ 0.1557
- 1 - ∏_{p≡1(4), p≥13}(1-2/p²) ≤ 0.0274
-/

/- THE GOAL: Prove SawhneyMain to complete the formalization.

This requires translating the paper's Lemmas 5, 6 and Proposition 1 above into Lean.

The key steps are:
1. Formalize the sieve bound (Lemma 5) - counting in residue classes
2. Formalize the squarefree density bound (Lemma 6) - off-diagonal constraint
3. Implement the casework from Proposition 1:
   - Case 1: A* has even element → density contradiction
   - Case 2: A* non-empty, all odd → density contradiction (two subcases)
   - Case 3: A* = ∅, mixing → density contradiction
   - Conclusion: A ⊆ A₇ or A ⊆ A₁₈

The numerical computations are explicit in the paper. Use η = 0.002.
-/

-- ============================================================================
-- SECTION 10B: PAPER-LEVEL ANALYTIC INPUTS (placeholders)
-- ============================================================================

/-
The remaining gap between this file and a `sorry`-free proof is the analytic number theory
in Lemmas 5 and 6 of the paper, plus the numerical inequalities used in the three cases of
Proposition 1.  These are recorded below as helper lemmas.

Each lemma should ultimately be proved from:
- a formalized version of Lemma 5 (a sieve bound in residue classes),
- a formalized version of Lemma 6 (squarefree density in arithmetic progressions),
- and the explicit numerical constants listed at the end of the paper section.
-/

/-- Proposition 1, Case 1: if `A*` contains an even element (i.e. an element not `7` or `18`
mod `25`), then the density condition `|A| ≥ (1/25 - η)N` fails for `η = 1/500` (i.e. `0.002`). -/
lemma case1_even_in_Astar_contradiction {N : ℕ} {A : Finset ℕ}
    (hAsub : A ⊆ Finset.range N) (hAprop : NonSquarefreeProductProp A)
    (heven : ∃ b ∈ A, b % 25 ≠ 7 ∧ b % 25 ≠ 18 ∧ 2 ∣ b) :
    (A.card : ℝ) < (1 / 25 - (1 / 500 : ℝ)) * (N : ℝ) := by
  -- Paper: Proposition 1, Case 1 (even element in A*)
  sorry

/-- Proposition 1, Case 2: if `A*` is nonempty and consists only of odd elements, then the
same density condition fails (again for `η = 1/500`). -/
lemma case2_all_odd_Astar_contradiction {N : ℕ} {A : Finset ℕ}
    (hAsub : A ⊆ Finset.range N) (hAprop : NonSquarefreeProductProp A)
    (hnonempty : ∃ b ∈ A, b % 25 ≠ 7 ∧ b % 25 ≠ 18)
    (hall_odd : ∀ b ∈ A, b % 25 ≠ 7 ∧ b % 25 ≠ 18 → ¬ 2 ∣ b) :
    (A.card : ℝ) < (1 / 25 - (1 / 500 : ℝ)) * (N : ℝ) := by
  -- Paper: Proposition 1, Case 2 (A* nonempty, all odd), including both subcases 2a and 2b.
  sorry

/-- Proposition 1, Case 3: if `A* = ∅` but both residues `7` and `18` occur in `A`, then the
same density condition fails (again for `η = 1/500`). -/
lemma case3_mixed_A7_A18_contradiction {N : ℕ} {A : Finset ℕ}
    (hAsub : A ⊆ Finset.range N) (hAprop : NonSquarefreeProductProp A)
    (hAstar_empty : ∀ b ∈ A, b % 25 = 7 ∨ b % 25 = 18)
    (hA7 : ∃ b ∈ A, b % 25 = 7) (hA18 : ∃ b ∈ A, b % 25 = 18) :
    (A.card : ℝ) < (1 / 25 - (1 / 500 : ℝ)) * (N : ℝ) := by
  -- Paper: Proposition 1, Case 3 (A* empty, both A7 and A18 nonempty).
  sorry

theorem sawhney_main : SawhneyMain := by
  -- The paper proves this with η = 0.002 and some N₀
  -- Need to translate Lemmas 5, 6 and the casework from Proposition 1
  classical
  -- We take η = 0.002 = 1/500, and any sufficiently large N₀ (here we take N₀ = 1).
  refine ⟨(1 / 500 : ℝ), 1, ?_⟩
  refine ⟨by norm_num, ?_, ?_⟩
  · -- 1/500 < 1/25
    norm_num
  · intro N hN A hAsub hAprop hDense
    -- Let A* be the elements not congruent to 7 or 18 mod 25.
    set Astar : Finset ℕ := A.filter (fun a => a % 25 ≠ 7 ∧ a % 25 ≠ 18)
    have hNpos : 0 < N := lt_of_lt_of_le (by decide : 0 < 1) hN
    by_cases hAstar : Astar = ∅
    · -- A* is empty: all elements are ≡ 7 or 18 (mod 25)
      have hAstar_empty' : ∀ b ∈ A, b % 25 = 7 ∨ b % 25 = 18 := by
        intro b hbA
        by_contra hcontra
        have hbAstar : b ∈ Astar := by
          have : b % 25 ≠ 7 ∧ b % 25 ≠ 18 := by
            simpa [not_or] using hcontra
          simpa [Astar, Finset.mem_filter, hbA, this]
        have : Astar.Nonempty := ⟨b, hbAstar⟩
        simpa [hAstar] using this
      -- If both residues occur, Case 3 contradicts density.
      by_cases hsub7 : A ⊆ A₇ N
      · exact Or.inl hsub7
      by_cases hsub18 : A ⊆ A₁₈ N
      · exact Or.inr hsub18
      -- Otherwise both residues occur (since every element is 7 or 18 mod 25).
      have hA7 : ∃ b ∈ A, b % 25 = 7 := by
        classical
        have : ∃ b, b ∈ A ∧ b ∉ A₁₈ N := by
          simpa [Finset.not_subset] using hsub18
        rcases this with ⟨b, hbA, hbNot⟩
        refine ⟨b, hbA, ?_⟩
        have hbmod : b % 25 = 7 ∨ b % 25 = 18 := hAstar_empty' b hbA
        cases hbmod with
        | inl h7 => exact h7
        | inr h18 =>
            exfalso
            apply hbNot
            -- b ∈ A implies b < N, so membership in A₁₈ N is equivalent to b % 25 = 18.
            have hbRange : b ∈ Finset.range N := hAsub hbA
            have hbLt : b < N := by simpa [Finset.mem_range] using hbRange
            simp [A₁₈, hbLt, h18]
      have hA18 : ∃ b ∈ A, b % 25 = 18 := by
        classical
        have : ∃ b, b ∈ A ∧ b ∉ A₇ N := by
          simpa [Finset.not_subset] using hsub7
        rcases this with ⟨b, hbA, hbNot⟩
        refine ⟨b, hbA, ?_⟩
        have hbmod : b % 25 = 7 ∨ b % 25 = 18 := hAstar_empty' b hbA
        cases hbmod with
        | inr h18 => exact h18
        | inl h7 =>
            exfalso
            apply hbNot
            have hbRange : b ∈ Finset.range N := hAsub hbA
            have hbLt : b < N := by simpa [Finset.mem_range] using hbRange
            simp [A₇, hbLt, h7]
      have hlt : (A.card : ℝ) < (1 / 25 - (1 / 500 : ℝ)) * (N : ℝ) :=
        case3_mixed_A7_A18_contradiction (N := N) (A := A) hAsub hAprop hAstar_empty' hA7 hA18
      exact (False.elim ((not_lt_of_ge hDense) hlt))
    · -- A* is nonempty: split into Cases 1 and 2 by parity.
      have hAstar_nonempty : ∃ b ∈ A, b % 25 ≠ 7 ∧ b % 25 ≠ 18 := by
        rcases (Finset.nonempty_iff_ne_empty.2 hAstar) with ⟨b, hbAstar⟩
        have hbA : b ∈ A := (Finset.mem_filter.1 hbAstar).1
        have hbmod : b % 25 ≠ 7 ∧ b % 25 ≠ 18 := (Finset.mem_filter.1 hbAstar).2
        exact ⟨b, hbA, hbmod.1, hbmod.2⟩
      by_cases heven : ∃ b ∈ A, b % 25 ≠ 7 ∧ b % 25 ≠ 18 ∧ 2 ∣ b
      · -- Case 1: there is an even element in A*
        have hlt : (A.card : ℝ) < (1 / 25 - (1 / 500 : ℝ)) * (N : ℝ) :=
          case1_even_in_Astar_contradiction (N := N) (A := A) hAsub hAprop heven
        exact (False.elim ((not_lt_of_ge hDense) hlt))
      · -- Case 2: all elements of A* are odd
        have hall_odd : ∀ b ∈ A, b % 25 ≠ 7 ∧ b % 25 ≠ 18 → ¬ 2 ∣ b := by
          intro b hbA hbmod
          intro hbEven
          apply heven
          exact ⟨b, hbA, hbmod.1, hbmod.2, hbEven⟩
        have hlt : (A.card : ℝ) < (1 / 25 - (1 / 500 : ℝ)) * (N : ℝ) :=
          case2_all_odd_Astar_contradiction (N := N) (A := A) hAsub hAprop hAstar_nonempty hall_odd
        exact (False.elim ((not_lt_of_ge hDense) hlt))

-- ============================================================================
-- SECTION 11: FINAL STATEMENTS (conditional on sawhney_main)
-- ============================================================================

theorem problem_848_statement_50 : Problem848Statement 50 := problem_848_N50
theorem problem_848_statement_100 : Problem848Statement 100 := problem_848_N100

/-- The full resolution (assuming SawhneyMain). -/
theorem problem_848_resolved : ∃ N₀ : ℕ, ∀ N ≥ N₀, Problem848Statement N :=
  problem_848_resolved_up_to_finite_check_of_sawhney sawhney_main

end Erdos.Problem848
