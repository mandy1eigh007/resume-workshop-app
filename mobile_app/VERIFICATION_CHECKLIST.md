# Final Verification Checklist

This checklist should be completed when testing the app in a Flutter environment.

## Pre-Launch Verification

### Content Loading
- [ ] App starts without crashing
- [ ] Home screen shows "Loading content from CONTENT_MASTER.md..." briefly
- [ ] Home screen shows success status with trade/skill/cert counts
- [ ] No error messages on home screen

### Resume Generation Screen
- [ ] Trade dropdown populates with 25+ trades
- [ ] Selecting a trade enables objective dropdown
- [ ] Objective dropdown shows "Apprenticeship Objectives:" header
- [ ] Objective dropdown shows "Job Objectives:" header
- [ ] Objectives are properly formatted (not truncated)
- [ ] Selecting an objective populates the text field
- [ ] Text field can be edited after selecting objective
- [ ] All trade names match CONTENT_MASTER.md exactly

### Skills Selector Widget
- [ ] Category dropdown shows: All Skills, Transferable, Job-Specific, Self-Management
- [ ] Selecting "All Skills" shows combined list
- [ ] Selecting "Transferable" shows only transferable skills
- [ ] Selecting "Job-Specific" shows only job-specific skills
- [ ] Selecting "Self-Management" shows only self-management skills
- [ ] FilterChips respond to taps
- [ ] Selected skills show with orange highlight
- [ ] Skill count updates when skills selected
- [ ] No duplicate skills displayed

### Artifact Upload Screen
- [ ] Artifact templates appear in horizontal scroll
- [ ] Template names are visible
- [ ] Field counts are correct
- [ ] Scrolling works smoothly
- [ ] No crashes when templates missing

### Measurable Bullet Form
- [ ] Form opens without errors
- [ ] Role suggestions toggle switch works
- [ ] Role dropdown populates when toggle enabled
- [ ] Selecting a role shows bullet examples
- [ ] Bullet examples are relevant to role
- [ ] Examples are properly formatted
- [ ] Form submission works

### Error Handling
- [ ] App works if CONTENT_MASTER.md temporarily unavailable
- [ ] Error message shown on home screen
- [ ] App doesn't crash
- [ ] Dropdowns show appropriate fallback messages
- [ ] User can still navigate and use basic features

## Content Accuracy Verification

### Objective Starters (Section A)
Verify at least these trades have objectives:
- [ ] Boilermaker (5 apprenticeship + 5 job = 10 total)
- [ ] Bricklayer / BAC Allied
- [ ] Carpenter (General)
- [ ] Carpenter – Interior Systems
- [ ] Millwright
- [ ] Pile Driver
- [ ] Cement Mason
- [ ] Drywall Finisher
- [ ] Electrician – Inside (01)
- [ ] Electrician – Limited Energy (06)
- [ ] Electrician – Residential (02)
- [ ] Elevator Constructor
- [ ] Floor Layer
- [ ] Glazier
- [ ] Heat & Frost Insulator
- [ ] Ironworker
- [ ] Laborer
- [ ] Operating Engineer
- [ ] Painter
- [ ] Plasterer
- [ ] Plumber / Steamfitter / HVAC-R
- [ ] Roofer
- [ ] Sheet Metal
- [ ] Sprinkler Fitter
- [ ] High Voltage – Outside Lineman
- [ ] Power Line Clearance Tree Trimmer

### Role Bullets (Section B)
Verify at least these roles have bullets:
- [ ] Line Cook
- [ ] Server
- [ ] Retail Associate
- [ ] Warehouse Associate
- [ ] Material Handler
- [ ] Traffic Control / Flagger
- [ ] Janitor/Custodian
- [ ] Security Guard
- [ ] Landscaper/Groundskeeper
- [ ] Demolition Laborer
- [ ] Carpenter Helper
- [ ] Drywall/Lather Helper
- [ ] Flooring Helper
- [ ] Concrete Laborer
- [ ] HVAC Helper
- [ ] Electrical Helper
- [ ] Plumbing Helper
- [ ] Sheet Metal Helper
- [ ] Ironworker Helper
- [ ] Roofer Helper

### Skills Canon (Section C)
- [ ] Transferable skills present (should be 10+ skills)
- [ ] Job-Specific skills present (should be 10+ skills)
- [ ] Self-Management skills present (should be 5+ skills)
- [ ] All skills properly separated by bullet points (•)
- [ ] No duplicate skills across categories

### Certifications (Section D)
- [ ] OSHA Outreach 10-Hour (Construction)
- [ ] OSHA Outreach 30-Hour (Construction)
- [ ] WA Flagger (expires three years from issuance)
- [ ] Forklift — employer evaluation on hire
- [ ] CPR/First Aid
- [ ] EPA Section 608 (if earned)

### Artifact Templates (Section G)
- [ ] Drop-Zone Control Checklist
- [ ] Tool Control Layout
- [ ] Study Log
- [ ] Maintenance Log (e.g., chainsaw)
- [ ] Timed Drill Log
- [ ] Nameplate/Print Read-Through

## Performance Testing
- [ ] Content loads in < 2 seconds on app start
- [ ] No lag when selecting trades
- [ ] No lag when selecting objectives
- [ ] Skill chips respond immediately to taps
- [ ] Scrolling is smooth in all lists
- [ ] No memory leaks during extended use

## Edge Cases
- [ ] Empty trade selection handled gracefully
- [ ] Empty role selection handled gracefully
- [ ] Very long objective text displays properly
- [ ] Special characters in content don't break parsing
- [ ] Trade names with special characters work (e.g., "Electrician – Inside (01)")

## Regression Testing
- [ ] Existing resume creation still works
- [ ] Artifact upload still works
- [ ] Progress tracking still works
- [ ] Quick wins still work
- [ ] Navigation between screens works
- [ ] Back button works everywhere

## Documentation Verification
- [ ] CONTENT_INTEGRATION.md is accurate
- [ ] INTEGRATION_SUMMARY.md matches implementation
- [ ] Code comments are helpful
- [ ] README mentions new features

## Code Quality
- [ ] No compiler warnings
- [ ] No analyzer warnings
- [ ] All tests pass
- [ ] No unused imports
- [ ] Proper error messages in logs

## Sign-Off
- [ ] All critical checks passed
- [ ] All content verified
- [ ] Performance acceptable
- [ ] Edge cases handled
- [ ] Documentation complete

**Tester Name:** ___________________
**Date:** ___________________
**Flutter Version:** ___________________
**Device/Emulator:** ___________________
**Notes:**
