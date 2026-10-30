# 26_R PR 규칙

해커톤 당일에는 모든 작업을 아래 흐름으로 올립니다.

**내 브랜치에서 작업 → GitHub에 push → PR로 리뷰 요청 → 리뷰어 승인 → develop에 머지**

## 1. 핵심 원칙

- **develop에서 직접 작업하지 않습니다.** develop은 팀 전체가 쓰는 완성본입니다.
- 리뷰 승인을 받은 PR만 develop에 들어갑니다.
- **한 브랜치 = 한 작업 = 한 PR**입니다. 머지된 브랜치는 계속 쓰지 않습니다.
- PR을 만든 뒤 **직접 Merge 버튼을 누르지 않고** 리뷰어의 승인을 기다립니다.
- 작은 단위로 자주 커밋합니다. (기능 하나, 수정 하나마다 커밋)

## 2. 브랜치 이름

영어 소문자와 하이픈(-)만 씁니다. 띄어쓰기와 한글은 쓰지 않습니다.

| 앞머리 | 언제 | 예시 |
| --- | --- | --- |
| `feat/` | 새 기능 추가 | `feat/risk-dashboard` |
| `fix/` | 버그 수정 | `fix/login-error` |
| `docs/` | 문서, README 수정 | `docs/readme-setup` |
| `practice/` | 이번 실습용 | `practice/hong` |

## 3. 작업 시작 전

작업할 때마다 develop을 최신으로 받은 뒤, 거기서 브랜치를 새로 땁니다.

```bash
git switch develop
git pull origin develop
git switch -c feat/작업이름
```

## 4. 커밋 메시지

`종류: 한 일` 형식으로 짧게 씁니다.

```
feat: 로그인 페이지 레이아웃 추가
fix: 위험도 점수 계산 오류 수정
docs: 실행 방법 추가
fix: 리뷰 반영 - 버튼 문구 수정
```

종류는 브랜치 앞머리와 같습니다. (`feat`, `fix`, `docs`)

## 5. PR 만들기

PR은 터미널이 아니라 **GitHub 웹사이트**에서 만듭니다.

1. push 후 저장소 페이지의 **Compare & pull request** 버튼을 누릅니다. (안 보이면 Pull requests 탭 → New pull request)
2. 위쪽이 `base: develop ← compare: 내 브랜치`인지 확인합니다.
3. 제목과 설명을 아래 템플릿대로 씁니다.
4. 오른쪽 **Reviewers**에서 리뷰어(컨펌 담당자)를 지정합니다.
5. **Create pull request**를 누릅니다.

### PR 설명 템플릿

```markdown
## 무엇을 했나요
-

## 확인 방법
-

## 스크린샷 (화면 작업이면)
```

### PR 올리기 전 확인

- [ ] 브랜치 이름이 규칙에 맞다.
- [ ] 커밋 메시지가 `종류: 한 일` 형식이다.
- [ ] base가 `develop`이고, compare가 내 브랜치다.
- [ ] 리뷰어를 지정했다.
- [ ] 화면 작업이면 스크린샷을 넣었다.

## 6. 리뷰 반영

수정 요청이 오면 **새 PR을 만들지 않습니다.** 같은 브랜치에서 고치고 커밋, 푸시하면 기존 PR에 자동으로 추가됩니다.

```bash
git add .
git commit -m "fix: 리뷰 반영 - 버튼 문구 수정"
git push
```

## 7. 머지 후 정리

리뷰어가 승인하고 Merge하면, 내 컴퓨터를 최신 develop으로 맞추고 다음 작업은 새 브랜치로 시작합니다.

```bash
git switch develop
git pull origin develop
git branch -d feat/작업이름
git switch -c feat/다음-작업
```

## 8. 리뷰어 역할

- 리뷰어(컨펌 담당자)가 PR을 확인하고 승인한 뒤 Merge합니다.
- 연습 단계에서는 일부러 수정 요청을 한 번씩 남겨서, 작성자가 리뷰 반영(6번)까지 경험하게 합니다.
- `CONFLICT`가 났다는 연락을 받으면 작성자가 혼자 해결하지 않게 하고, 화면 공유로 함께 해결합니다.

## 9. 금지 사항

- develop에서 직접 작업하거나 develop에 바로 push
- 승인 없이 본인이 Merge
- 머지된 브랜치를 계속 사용
- 한 PR에 여러 작업 섞기
- 충돌(`CONFLICT`)을 혼자 해결하려고 하기 → 컨펌 담당자에게 화면 공유

## 자주 나는 문제

| 메시지 | 해결 |
| --- | --- |
| `! [rejected] ... (fetch first)` | `git pull origin 내브랜치` 후 다시 `git push` |
| `Permission denied` / `403` | 26_R 초대 수락 확인, 로그인 계정 확인 후 다시 push |
| `CONFLICT (content)` | 혼자 해결하지 말고 컨펌 담당자에게 화면 공유 |
| develop에서 실수로 작업함 (커밋 전) | 그대로 `git switch -c feat/새브랜치` 하면 수정 내용이 따라옴 |

모르겠으면 에러 메시지 전체를 **텍스트로 복사**해서 팀 채팅방에 올립니다.
