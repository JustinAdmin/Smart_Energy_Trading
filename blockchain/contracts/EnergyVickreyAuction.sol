// SPDX-License-Identifier: MIT
pragma solidity ^0.8.13;

// Vickrey auction contract
contract EnergyVickreyAuction {
    struct Bid {
        bytes32 sealedBid;
        uint256 deposit;
    }

    address public seller;
    uint256 public biddingStart;
    uint256 public biddingEnd;
    uint256 public revealEnd;
    bool public ended;
    uint256 public biddingDuration; // Bidding phase duration
    uint256 public revealDuration;  // Reveal phase duration

    mapping(address => Bid) public bids;
    address[] public bidders;

    address public highestBidder;
    uint256 public highestBid;
    uint256 public secondHighestBid;

    event BidPlaced(address indexed bidder, uint256 deposit);
    event BidRevealed(address indexed bidder, uint256 value);
    event AuctionEnded(address winner, uint256 winningBid);
    event AuctionReset();

    modifier onlyBefore(uint256 _time) {
        require(block.timestamp < _time, "Too late");
        _;
    }

    modifier onlyAfter(uint256 _time) {
        require(block.timestamp > _time, "Too early");
        _;
    }

    modifier auctionNotEnded() {
        require(!ended, "Auction already ended");
        _;
    }

    constructor(uint256 _biddingDuration, uint256 _revealDuration) {
        seller = msg.sender;
        biddingDuration = _biddingDuration;
        revealDuration = _revealDuration;
    }

    // Start the auction with correct timing logic
    function startAuction() external {
        require(biddingStart == 0, "Auction has already started");
        biddingStart = block.timestamp;
        biddingEnd = biddingStart + biddingDuration;
        revealEnd = biddingEnd + revealDuration;
    }

    // Place bid
    function bid(bytes32 _sealedBid) external payable onlyBefore(biddingEnd) {
        require(bids[msg.sender].sealedBid == bytes32(0), "Already bid");
        require(msg.value > 0, "Deposit must be greater than 0");

        bids[msg.sender] = Bid({
            sealedBid: _sealedBid,
            deposit: msg.value
        });
        bidders.push(msg.sender);

        emit BidPlaced(msg.sender, msg.value);
    }

    // Reveal bids
    function reveal(uint256 _value, string calldata _nonce)
        external
        onlyAfter(biddingEnd)
        onlyBefore(revealEnd)
    {
        Bid storage bidToCheck = bids[msg.sender];
        require(bidToCheck.sealedBid != bytes32(0), "No bid found");

        require(
            bidToCheck.sealedBid == keccak256(abi.encodePacked(_value, _nonce)),
            "Invalid bid reveal"
        );
        require(bidToCheck.deposit >= _value, "Deposit too low");

        if (_value > highestBid) {
            secondHighestBid = highestBid;
            highestBid = _value;
            highestBidder = msg.sender;
        } else if (_value > secondHighestBid) {
            secondHighestBid = _value;
        }

        emit BidRevealed(msg.sender, _value);
    }

    // Finalize auction
    function finalizeAuction() external onlyAfter(revealEnd) auctionNotEnded {
        ended = true;

        if (highestBidder != address(0)) {
            payable(seller).transfer(secondHighestBid);
            payable(highestBidder).transfer(
                bids[highestBidder].deposit - secondHighestBid
            );
        }

        for (uint256 i = 0; i < bidders.length; i++) {
            address bidder = bidders[i];
            if (bidder != highestBidder) {
                uint256 refundAmount = bids[bidder].deposit;
                bids[bidder].deposit = 0;
                if (refundAmount > 0) {
                    payable(bidder).transfer(refundAmount);
                }
            }
        }

        emit AuctionEnded(highestBidder, secondHighestBid);
    }

    // Reset auction
    function resetAuction(uint256 _biddingDuration, uint256 _revealDuration) external {
        require(ended, "Auction must be ended before resetting");

        biddingStart = 0;
        biddingEnd = block.timestamp + _biddingDuration;
        revealEnd = biddingEnd + _revealDuration;
        ended = false;
        highestBidder = address(0);
        highestBid = 0;
        secondHighestBid = 0;

        for (uint256 i = 0; i < bidders.length; i++) {
            delete bids[bidders[i]];
        }
        delete bidders;

        emit AuctionReset();
    }

    // Get current block timestamp
    function revealTimestamp() external view returns (uint256) {
        return block.timestamp;
    }

    // Get bidding start time
    function getBiddingStart() external view returns (uint256) {
        require(biddingStart > 0, "Auction has not started yet");
        return biddingStart;
    }

    // Get reveal start time
    function getRevealStart() external view returns (uint256) {
        require(biddingStart > 0, "Auction has not started yet");
        return biddingEnd;
    }
}
