// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract RunningStats {
    uint256 public totalKm = 0;
    uint256 public runs = 0;
    
    function logRun(uint256 _km) external {
        totalKm += _km;
        runs += 1;
    }
}
