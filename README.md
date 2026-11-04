# API CI・이미지 게시 테스트

기존 test.txt를 유지하며 FastAPI 실행 기반과 GitHub Actions를 검증하는 개인 테스트 저장소입니다.

- [협업 규칙](CONTRIBUTING.md)
- [이미지 게시 가이드](docs/infra/IMAGE_RELEASE.md)
- [API 실행 안내](api/README.md)

일반 작업은 develop 대상 PR, develop 병합 후 API CI 재검증과 GHCR 게시가 실행됩니다. 서버 CD는 아직 연결하지 않았습니다.

- [ECS CD 기본 설정 초안](infra/ecs/README.md)
