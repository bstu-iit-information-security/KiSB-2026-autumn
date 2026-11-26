#pragma once
#include <array>
#include <cstddef>
#include <cstdint>

// Блочный шифр СТБ 34.101.31 (БелТ): блок 128 бит, ключ 256 бит
constexpr std::size_t BLOCK_SIZE = 16;
constexpr std::size_t KEY_SIZE = 32;

using Block = std::array<std::uint8_t, BLOCK_SIZE>;
using Key = std::array<std::uint8_t, KEY_SIZE>;

Block encrypt_block(const Block& pt_block, const Key& key);
Block decrypt_block(const Block& ct_block, const Key& key);
